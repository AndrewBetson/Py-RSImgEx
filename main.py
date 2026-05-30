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
parser.add_argument( '-v', '--version', type=str, choices=( '1', '1X', '2' ), help='Archive version we\'re dealing with. 1 = III/VC/Bully, 1X = III/VC XBOX, 2 = SA', required=True )
parser.add_argument( '-e', '--extract', type=str, default='', help='Extract a file in the archive to the path set by -o|--output.' )
parser.add_argument( '-x', '--extract-all', action='store_true', help='Extract all files in the archive to the path set by -o|--output.' )
parser.add_argument( '-l', '--list', action='store_true', help='List all files in the archive.' )
args = parser.parse_args()

if not args.input.exists():
	raise Exception( f'Error: Input file "{args.input}" does not exist.' )

if not args.input.name.lower().endswith( '.img' ):
	raise Exception( f'Error: Input file "{args.input}" is not a .img file.' )

if not args.extract and not args.extract_all and not args.list:
	raise Exception( 'Error: Nothing to do! Pass -e|--extract <file>, -x|--extract-all, or -l|--list to operate on the archive!' )

version = EImgVersion.III_VC
match args.version.lower():
	case '1': version = EImgVersion.III_VC
	case '1x': version = EImgVersion.III_VC_XBOX
	case '2': version = EImgVersion.SA

archive = ImgArchive.from_path( args.input, version )

if args.extract != '' and args.extract != '*':
	if not args.output.exists():
		os.makedirs( args.output )

	archive.extract_file( args.extract, args.output )

if args.extract_all or args.extract == '*':
	if not args.output.exists():
		os.makedirs( args.output )

	archive.extract_all( args.output )

if args.list:
	for f in archive.files:
		print( f'{f.name}' )
