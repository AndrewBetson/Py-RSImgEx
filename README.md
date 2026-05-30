Python utility that extracts or lists files from (most) sixth generation Rockstar IMG archives.

# Supported Formats
- Version 1 (III/VC/Bully)
- Version 1x (III/VC XBOX)
- Version 2 (SA)

# Usage
Install dependencies using `pip install -r requirements.txt`

## Extract a file from an archive
`python main.py -i|--input <-o|--output ./extract_dir> ./gta3.img -v 1|1x|2 -e|--extract file_to_extr.act`

## Extract all files from an archive
`python main.py -i|--input <-o|--output ./extract_dir> ./gta3.img -v 1|1x|2 -x|--extract-all`

## List all files in an archive
`python main.py -i|--input ./gta3.img -v 1|1x|2 -l|--list`

# License
This utility is licensed under version 3 of the GNU General Public License.

For more information, see `LICENSE.md`.

Special thanks to the GTAMods wiki for their article detailing this format and the compression used by the XBOX versions of III/VC.
(https://gtamods.com/wiki/IMG_archive)

This utility was developed without the assistance of generative *"AI"*.
