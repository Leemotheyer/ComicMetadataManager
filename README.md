# Comic Metadata Manager

A companion app to go along with Kapowarr to be able to be able to generate ComicInfo.xml for all your downloaded issues using the ComicVine API.

## Features

- **Volume Management**: Browse and search through comic volumes from Kapowarr
- **Metadata Fetching**: Automatically retrieve comic metadata from ComicVine
- **XML Generation**: Create ComicInfo.xml files for comic archives
- **Caching System**: Database-backed caching for improved performance
- **Web Interface**: Modern, responsive web GUI for easy management

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
- `temp_directory`: Directory for temporary files
- `max_concurrent_tasks`: Maximum concurrent processing tasks

These can be set from the web GUI in the settings page

## Usage

1. **Browse Volumes**: View all available comic volumes
2. **Get Metadata**: Fetch metadata for specific volumes
3. **Generate XML**: Create ComicInfo.xml files for comic archives
4. **Settings**: Configure API keys and application settings


## License

This project is open source and available under the MIT License.
