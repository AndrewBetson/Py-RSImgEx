# SPDX-FileCopyrightText: © Andrew Betson
# SPDX-License-Identifier: GPL-3.0-or-later

import argparse, os
from pathlib import Path

from img import *

parser = argparse.ArgumentParser(
	prog='RSImgEx',
	description='Extracts (most) sixth generation Rockstar IMG archives.'
)
parser.add_argument( '-i', '--input', type=Path, help='File to operate on.', required=True )
parser.add_argument( '-o', '--output', default='./out', type=Path, help='Path to save extracted files to.' )
parser.add_argument( '-d', '--decrypt', action='store_true', help='Decrypt the archive. Only applicable to version 3 (GTA IV) archives.' )
parser.add_argument( '-e', '--extract', type=str, default='', help='Extract a file in the archive to the path set by -o|--output.' )
parser.add_argument( '-x', '--extract-all', action='store_true', help='Extract all files in the archive to the path set by -o|--output.' )
parser.add_argument( '--info', action='store_true', help='Print information about each file in the archive.' )
args = parser.parse_args()

if not args.input.exists():
	raise Exception( f'Error: Input file "{args.input}" does not exist.' )

if not args.input.name.lower().endswith( '.img' ):
	raise Exception( f'Error: Input file "{args.input}" is not a .img file.' )

if not args.decrypt and not args.extract and not args.extract_all and not args.info:
	raise Exception( 'Error: Nothing to do! Pass -d|--decrypt, -e|--extract <file>, -x|--extract-all, or -i|--info to operate on the archive!' )

archive = ImgArchive.from_path( args.input )

if args.decrypt:
	archive.decrypt()

if args.extract != '' and args.extract != '*':
	if not args.output.exists():
		os.makedirs( args.output )

	archive.extract_file( args.extract, args.output )

if args.extract_all or args.extract == '*':
	if not args.output.exists():
		os.makedirs( args.output )

	archive.extract_all( args.output )

if args.info:
	archive.info()
