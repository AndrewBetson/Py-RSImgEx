# SPDX-FileCopyrightText: © Andrew Betson
# SPDX-License-Identifier: GPL-3.0-or-later

import enum, io, os, lzo
from enum import IntEnum
from pathlib import Path

SECTOR_SIZE = 2048

@enum.unique
class EImgVersion( IntEnum ):
	III_VC = 0
	III_VC_XBOX = 1
	SA = 2

class ImgDirEntryV1:
	offset: int
	size: int
	name: str

	@classmethod
	def from_stream( cls, stream: io.BufferedReader ):
		o = cls()

		o.offset = int.from_bytes( stream.read( 4 ), 'little' ) * SECTOR_SIZE
		o.size = int.from_bytes( stream.read( 4 ), 'little' ) * SECTOR_SIZE
		o.name = stream.read( 24 ).decode().split( '\x00', 1 )[ 0 ]

		return o

class ImgDirEntryV2:
	offset: int
	streaming_size: int
	size: int
	name: str

	@classmethod
	def from_stream( cls, stream: io.BufferedReader ):
		o = cls()

		o.offset = int.from_bytes( stream.read( 4 ), 'little' ) * SECTOR_SIZE
		o.streaming_size = int.from_bytes( stream.read( 2 ), 'little' ) * SECTOR_SIZE
		o.size = int.from_bytes( stream.read( 2 ), 'little' ) * SECTOR_SIZE

		# Every file in SA has extra (garbage?) data after it's name,
		# so we need to split the bytes *before* decoding them.
		o.name = stream.read( 24 ).split( b'\x00' )[ 0 ].decode()

		return o

class ImgArchive:
	files: list[ ImgDirEntryV1 | ImgDirEntryV2 ] = list[ ImgDirEntryV1 | ImgDirEntryV2 ]()

	_path: Path
	_version: EImgVersion

	@classmethod
	def from_path( cls, path: Path, version: EImgVersion ):
		o = cls()

		o._path = path
		o._version = version

		dir_file = path
		if version == EImgVersion.III_VC or version == EImgVersion.III_VC_XBOX:
			dir_file = Path( f'{os.path.splitext( path )[ 0 ]}.dir' )
			if not dir_file.exists():
				print( f'Error: Failed to find matching .dir file for input file {path}. Is this a version 1/1X IMG archive?' )
				exit( -1 )

		with open( dir_file, 'rb' ) as dir:
			if version == EImgVersion.III_VC or version == EImgVersion.III_VC_XBOX:
				dir.seek( 0, os.SEEK_END )
				num_files = int( dir.tell() / 32 )
				dir.seek( 0, os.SEEK_SET )
				for _ in range( num_files ):
					o.files.append( ImgDirEntryV1.from_stream( dir ) )
			else:
				magic = dir.read( 4 )
				if magic != b'VER2':
					print( 'Error: Failed to find VER2 magic at beginning of provided IMG archive. Is this a version 2 IMG archive?' )
					exit( -1 )

				num_files = int.from_bytes( dir.read( 4 ), 'little' )
				for _ in range( num_files ):
					o.files.append( ImgDirEntryV2.from_stream( dir ) )

		return o

	def extract_all( self, out_path: Path ):
		with open( self._path, 'rb' ) as img:
			for f in self.files:
				self._do_extraction( f, out_path, img )

	def extract_file( self, file: str, out_path: Path ):
		entry = None
		for f in self.files:
			if f.name == file:
				entry = f
				break

		if entry == None:
			print( f'Error: Failed to find file "{file}" in provided IMG archive.' )
			exit( 0 )

		with open( self._path, 'rb' ) as img:
			self._do_extraction( entry, out_path, img )

		return

	def _do_extraction( self, file: ImgDirEntryV1|ImgDirEntryV2, out_path: Path, stream: io.BufferedReader ):
		stream.seek( file.offset, os.SEEK_SET )
		data = bytearray()
		if self._version == EImgVersion.III_VC:
			data += stream.read( file.size )
		elif self._version == EImgVersion.III_VC_XBOX:
			cmp_magic = int.from_bytes( stream.read( 4 ), 'little' )

			if cmp_magic != 0x67A3A1CE and cmp_magic != 0xCEA1A367:
				stream.seek( -4, os.SEEK_CUR )
				data = stream.read( file.size )
			else:
				stream.read( 4 ) # checksum, we don't need this.
				stream.read( 4 ) # total compressed size, including the compression header.

				while 1:
					# If this is the intended way to check if
					# we've reached the last chunk, it's really stupid.
					test = int.from_bytes( stream.read( 4 ), 'little' ) # unknown, always(?) 0x04000000.
					if test != 0x04:
						stream.seek( -4, os.SEEK_CUR )

						# Read the garbage data after the actual data
						# for completeness' sake.
						data += stream.read( file.size - ( stream.tell() - file.offset ) )

						break
					else:
						decmp_size = int.from_bytes( stream.read( 4 ), 'little' )
						cmp_size = int.from_bytes( stream.read( 4 ), 'little' )

						# We don't actually know how big the decompressed data is
						# because the field that's meant to store it in the compression
						# header just stores the compressed size again.
						#
						# So just multiply it by 16, whatever man.
						data += lzo.decompress( stream.read( cmp_size ), False, decmp_size * 16, algorithm='LZO1X' )
		else:
			data += stream.read( file.streaming_size ) # type: ignore

		out_file = open( out_path.joinpath( file.name ), 'wb' )
		out_file.write( data )
		out_file.close()
		return
