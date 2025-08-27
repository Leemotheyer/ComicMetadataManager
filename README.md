# Comic Metadata Manager

A companion app to go along with Kapowarr to be able to be able to generate ComicInfo.xml for all your downloaded issues using the ComicVine API.

## Features

- **Volume Management**: Browse and search through comic volumes from Kapowarr
- **Metadata Fetching**: Automatically retrieve comic metadata from ComicVine
- **XML Generation**: Create ComicInfo.xml files for comic archives
- **Caching System**: Database-backed caching for improved performance
- **Web Interface**: Modern, responsive web GUI for easy management

Does not currently support rar/cbr file formats.
zip/cbz work as intened and within Kapowarr you can convert all files to zip/cbz

## Quick Start

### Prerequisites

- Python 3.7+
- Kapowarr API key
- ComicVine API key

### Installation

1. Clone the repository

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Run the application:
   ```bash
   python app.py
   ```

4. Open your browser to `http://localhost:5000`

## Configuration

The application automatically creates a `config/config.json` file on first run if none exists. This makes setup much easier!

### Key Settings
The application uses `config/config.json` for configuration. Key settings include:

- `kapowarr_url`: Your Kapowarr server URL
- `kapowarr_api_key`: Your Kapowarr API key
- `comicvine_api_key`: Your ComicVine API key
- `kapowarr_parent_folder`: Parent folder path from Kapowarr (e.g., "/comics-1") to map to local "/comics" folder
- `temp_directory`: Directory for temporary files
- `max_concurrent_tasks`: Maximum concurrent processing tasks for manual operations
- `max_concurrent_metadata_tasks`: Maximum concurrent tasks for scheduled metadata processing

These can be set from the web GUI in the settings page

## Path Mapping

The application includes a path mapping feature that allows you to map Kapowarr folder paths to your local file system paths. This is useful when Kapowarr uses a different folder structure than your local setup.

### Example
- **Kapowarr folder**: `/comics-1/DC Comics/Batgirl (2025)`
- **Local folder**: `/comics/DC Comics/Batgirl (2025)`
- **Setting**: Set `kapowarr_parent_folder` to `/comics-1`

The application will automatically convert all Kapowarr paths starting with `/comics-1` to use `/comics` as the local parent folder, preserving the relative path structure.

## Usage

1. **Browse Volumes**: View all available comic volumes
2. **Get Metadata**: Fetch metadata for specific volumes
3. **Generate XML**: Create ComicInfo.xml files for comic archives
4. **Settings**: Configure API keys and application settings


## License

This project is open source and available under the MIT License.
