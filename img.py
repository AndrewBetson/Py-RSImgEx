# SPDX-FileCopyrightText: © Andrew Betson
# SPDX-License-Identifier: GPL-3.0-or-later

import enum, io, os, lzo
from Crypto.Cipher import AES
from enum import IntEnum
from pathlib import Path

SECTOR_SIZE = 2048
MAX_DECOMPRESSED_BLOCK_SIZE = 131072
COMPRESSED_BLOCK_HEADER_SIZE = 12

# Technically having this here is dubiously illegal but the alternatives are super inconvenient, so whatever.
GTAIV_AES_KEY = b'\x1A\xB5\x6F\xED\x7E\xC3\xFF\x01\x22\x7B\x69\x15\x33\x97\x5D\xCE\x47\xD7\x69\x65\x3F\xF7\x75\x42\x6A\x96\xCD\x6D\x53\x07\x56\x5D'

@enum.unique
class EImgVersion( IntEnum ):
	III_VC_Bully = 0
	SA = 1
	IV = 2

class ImgTOCEntry:
	offset: int
	size: int
	name: str

	@classmethod
	def from_stream( cls, stream: io.BufferedReader, version: EImgVersion ):
		o = cls()

		if version == EImgVersion.IV:
			# Unknown. GTAMods wiki claims this is "Itemsize"
			# but it absolutely is not lmfao.
			stream.read( 4 )

			# Resource type ID, we don't really need this.
			stream.read( 4 )

		o.offset = int.from_bytes( stream.read( 4 ), 'little' ) * SECTOR_SIZE

		if version == EImgVersion.SA or version == EImgVersion.IV:
			o.size = int.from_bytes( stream.read( 2 ), 'little' ) * SECTOR_SIZE

			# Unused duplicate of size in SA's case,
			# unknown short in IV's case.
			stream.read( 2 )
		else:
			o.size = int.from_bytes( stream.read( 4 ), 'little' ) * SECTOR_SIZE

		if version == EImgVersion.III_VC_Bully or version == EImgVersion.SA:
			o.name = stream.read( 24 ).split( b'\x00' )[ 0 ].decode()

		return o

class ImgArchive:
	toc = list[ ImgTOCEntry ]()

	_data_path: Path
	_toc_path: Path
	_version: EImgVersion
	_is_encrypted: bool

	@classmethod
	def from_path( cls, path: Path ):
		o = cls()

		o._data_path = path

		dir_file = Path( f'{os.path.splitext( path )[ 0 ]}.dir' )
		version = EImgVersion.III_VC_Bully
		is_encrypted = False

		# This will unfortunately cause issues for people who have
		# an SA gta3.img in the same folder as a III/VC gta3.dir,
		# but encrypted IV archives give us no other option that I can think of.
		if not dir_file.exists():
			with open( path, 'rb' ) as img:
				magic = img.read( 4 )
				if magic == b'VER2':
					dir_file = path
					version = EImgVersion.SA
				elif magic == b'R*N\xA9':
					dir_file = path
					version = EImgVersion.IV
				else:
					# Assume we're an encrypted IV archive.
					dir_file = path
					version = EImgVersion.IV
					is_encrypted = True

		o._version = version
		o._toc_path = dir_file
		o._is_encrypted = is_encrypted

		if is_encrypted:
			return o

		o._initialize_toc()

		return o

	def decrypt( self ):
		if not self._is_encrypted:
			return

		with open( self._data_path, 'r+b' ) as img:
			data = bytearray()
			aes = AES.new( GTAIV_AES_KEY, mode=AES.MODE_ECB )

			header = img.read( 16 )
			for _ in range( 16 ):
				header = aes.decrypt( header )
			data += header

			magic = data[ :4 ]
			if magic != b'R*N\xa9':
				raise Exception( f'Error: Found incorrect magic {magic} while decrypting file "{self._data_path}". Is this an encrypted version 3 archive?' )

			num_files = int.from_bytes( data[ 8:12 ], 'little' )
			table_size = int.from_bytes( data[ 12:16 ], 'little' )

			# Table entry size (which we already know)
			# and an unknown short.
			data += img.read( 4 )

			num_file_name_chunks = int( ( table_size - ( num_files * 16 ) ) / 16 )
			remaining_file_name_bytes = table_size - ( int( table_size / 16 ) * 16 )

			for _ in range( num_files ):
				chunk = img.read( 16 )
				for _ in range( 16 ):
					chunk = aes.decrypt( chunk )
				data += chunk

			for _ in range( num_file_name_chunks ):
				chunk = img.read( 16 )
				for _ in range( 16 ):
					chunk = aes.decrypt( chunk )
				data += chunk

			# Read the last <16 unencrypted file name bytes.
			data += img.read( remaining_file_name_bytes )

			img.seek( 0, os.SEEK_SET )
			img.write( data )

		self._initialize_toc()

	def extract_all( self, out_path: Path ):
		if self._is_encrypted:
			raise Exception( f'Error: Attempted to extract all files from encrypted archive "{self._data_path}". Decrypt this archive before attempting to operate on it.' )

		with open( self._data_path, 'rb' ) as img:
			for f in self.toc:
				self._do_extraction( f, out_path, img )

	def extract_file( self, file: str, out_path: Path ):
		if self._is_encrypted:
			raise Exception( f'Error: Attempted to extract file "{file}" from encrypted archive "{self._data_path}". Decrypt this archive before attempting to operate on it.' )

		entry = None
		for f in self.toc:
			if f.name == file:
				entry = f
				break

		if entry == None:
			raise Exception( f'Error: Failed to find file "{file}" in provided IMG archive.' )

		with open( self._data_path, 'rb' ) as img:
			self._do_extraction( entry, out_path, img )

	def info( self ):
		for f in self.toc:
			print( f'{f.name}:\n\tOffset:\t{f.offset}\n\tSize:\t{f.size}' )

	def _initialize_toc( self ):
		if not self._toc_path.exists():
			raise Exception( f'Error: Failed to find directory file "{self._toc_path}".' )

		with open( self._toc_path, 'rb' ) as dir:
			if self._version == EImgVersion.III_VC_Bully:
				dir.seek( 0, os.SEEK_END )
				num_files = int( dir.tell() / 32 )
				dir.seek( 0, os.SEEK_SET )

				for _ in range( num_files ):
					self.toc.append( ImgTOCEntry.from_stream( dir, EImgVersion.III_VC_Bully ) )
			elif self._version == EImgVersion.SA:
				# Magic, which we've already validated.
				dir.read( 4 )

				num_files = int.from_bytes( dir.read( 4 ), 'little' )
				for _ in range( num_files ):
					self.toc.append( ImgTOCEntry.from_stream( dir, EImgVersion.SA ) )
			elif self._version == EImgVersion.IV:
				magic = dir.read( 4 )
				if magic != b'R*N\xA9':
					raise Exception( f'Error: Found incorrect magic while initializing version 3 archive "{self._data_path}".' )

				# Version, should always be 3 if the magic is correct.
				dir.read( 4 )

				num_files = int.from_bytes( dir.read( 4 ), 'little' )
				table_size = int.from_bytes( dir.read( 4 ), 'little' )

				# Table entry size (which we already know)
				# and an unknown short.
				dir.read( 4 )

				for _ in range( num_files ):
					self.toc.append( ImgTOCEntry.from_stream( dir, EImgVersion.IV ) )

				name_table_size = table_size - ( num_files * 16 )
				name_table = dir.read( name_table_size )
				name_table = name_table.split( b'\x00' )

				for i, f in enumerate( self.toc ):
					f.name = name_table[ i ].decode()

	def _do_extraction( self, file: ImgTOCEntry, out_path: Path, stream: io.BufferedReader ):
		stream.seek( file.offset, os.SEEK_SET )
		data = bytearray()
		if self._version == EImgVersion.III_VC_Bully:
			cmp_magic = int.from_bytes( stream.read( 4 ), 'little' )

			if cmp_magic != 0x67A3A1CE:
				stream.seek( -4, os.SEEK_CUR )
				data = stream.read( file.size )
			else:
				# Checksum, we don't need this.
				stream.read( 4 )

				total_cmp_size = int.from_bytes( stream.read( 4 ), 'little' )

				num_cmp_bytes_read = 0
				while 1:
					# Unknown, always 0x04000000
					stream.read( 4 )

					if num_cmp_bytes_read >= total_cmp_size:
						stream.seek( -4, os.SEEK_CUR )

						# Read the garbage data after the actual data
						# for completeness' sake.
						data += stream.read( file.size - ( stream.tell() - file.offset ) )

						break
					else:
						# In theory this is supposed to be the decompressed size,
						# but in practice it's always the same as the compressed size.
						stream.read( 4 )
						cmp_size = int.from_bytes( stream.read( 4 ), 'little' )

						data += lzo.decompress( stream.read( cmp_size ), False, MAX_DECOMPRESSED_BLOCK_SIZE, algorithm='LZO1X' )

						num_cmp_bytes_read += cmp_size + COMPRESSED_BLOCK_HEADER_SIZE
		elif self._version == EImgVersion.SA:
			data += stream.read( file.size )
		elif self._version == EImgVersion.IV:
#			stream.seek( file.offset, os.SEEK_SET )
			data += stream.read( file.size )

		out_file = open( out_path.joinpath( file.name ), 'wb' )
		out_file.write( data )
		out_file.close()
