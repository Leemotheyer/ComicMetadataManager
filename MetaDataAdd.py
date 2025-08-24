import os
import patoolib
import shutil
import sys

def main():
    # Check command line arguments
    if len(sys.argv) != 3:
        print("Usage: python metatest.py <comic_file> <xml_file>")
        print("Example: python metatest.py 'comic.cbr' 'metadata.xml'")
        sys.exit(1)
    
    # Get filenames from command line
    comic_filename = sys.argv[1]
    xml_filename = sys.argv[2]
    
    # Validate input files exist
    if not os.path.exists(comic_filename):
        print(f"Error: Comic file '{comic_filename}' not found!")
        sys.exit(1)
    
    if not os.path.exists(xml_filename):
        print(f"Error: XML file '{xml_filename}' not found!")
        sys.exit(1)
    
    # Get base name without extension for directory
    base_name = os.path.splitext(comic_filename)[0]
    outdir = f"./{base_name}"
    
    print(f"Processing comic file: {comic_filename}")
    print(f"Using XML metadata: {xml_filename}")
    print(f"Extracting to directory: {outdir}")
    
    # Extract the comic file
    print(f"Extracting {comic_filename} to {outdir}...")
    patoolib.extract_archive(comic_filename, outdir=outdir)
    
    # Look for comicinfo.xml in extracted and delete it
    xml_path = os.path.join(outdir, "ComicInfo.xml")
    if os.path.exists(xml_path):
        print("Removing existing ComicInfo.xml...")
        os.remove(xml_path)
    
    # Copy XML file to extracted directory
    print(f"Copying {xml_filename} to {xml_path}...")
    shutil.copy2(xml_filename, xml_path)
    
    # Create new CBR file
    print("Creating new CBR file...")
    
    # Change to extracted directory
    os.chdir(outdir)
    
    # List all files in current directory
    files = [f for f in os.listdir('.') if os.path.isfile(f)]
    print(f"Files to archive: {files}")
    
    # Create new archive with a temporary name first
    temp_filename = f"../temp_{os.path.basename(comic_filename)}"
    print(f"Creating temporary archive: {temp_filename}")
    patoolib.create_archive(temp_filename, files)
    
    # Change back to parent directory for cleanup
    os.chdir('..')
    
    # Create backup of original file
    backup_filename = f"{comic_filename}.backup"
    print(f"Creating backup: {backup_filename}")
    os.rename(comic_filename, backup_filename)
    
    # Rename new file to original filename
    print(f"Renaming new file to {comic_filename}")
    os.rename(os.path.basename(temp_filename), comic_filename)
    
    # Clean up extracted directory
    print(f"Cleaning up {outdir}...")
    shutil.rmtree(outdir)
    
    # Remove backup file
    print(f"Removing backup file...")
    os.remove(backup_filename)
    
    # Remove the used XML file
    print(f"Removing used XML file: {xml_filename}")
    os.remove(xml_filename)
    
    print(f"Done! {comic_filename} has been updated with new metadata.")

if __name__ == "__main__":
    main()



