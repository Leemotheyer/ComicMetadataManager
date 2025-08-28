import json
import os
import xml.etree.ElementTree as ET
from xml.dom import minidom
from typing import Dict, List, Optional
import re
from datetime import datetime

class ComicInfoXMLGenerator:
    def __init__(self):
        self.xmlns = "https://raw.githubusercontent.com/anansi-project/comicinfo/refs/heads/main/schema/v2.0/ComicInfo.xsd"
    
    def clean_text(self, text: str) -> str:
        """Clean HTML tags and special characters from text"""
        if not text:
            return ""
        
        # Remove HTML tags
        text = re.sub(r'<[^>]+>', '', text)
        # Decode HTML entities
        text = text.replace('&lt;', '<').replace('&gt;', '>').replace('&amp;', '&')
        text = text.replace('\u003c', '<').replace('\u003e', '>').replace('\u003cp\u003e', '').replace('\u003c/p\u003e', '')
        text = text.replace('\u003cem\u003e', '').replace('\u003c/em\u003e', '')
        # Clean up extra whitespace
        text = re.sub(r'\s+', ' ', text).strip()
        return text
    
    def format_credits(self, credits: List[Dict], role_key: str = 'role') -> str:
        """Format creator credits into a readable string"""
        if not credits:
            return ""
        
        # Group by role
        role_groups = {}
        for credit in credits:
            role = credit.get(role_key, 'Unknown')
            name = credit.get('name', 'Unknown')
            if role not in role_groups:
                role_groups[role] = []
            role_groups[role].append(name)
        
        # Format as "Role: Name1, Name2; Role2: Name3, Name4"
        formatted_credits = []
        for role, names in role_groups.items():
            role_credits = f"{role.title()}: {', '.join(names)}"
            formatted_credits.append(role_credits)
        
        return "; ".join(formatted_credits)
    
    def create_comic_info_xml(self, issue_data: Dict) -> str:
        """Create ComicInfo.xml content for a single issue"""
        kapowarr_issue = issue_data.get('kapowarr_issue', {})
        comicvine_metadata = issue_data.get('comicvine_metadata', {})
        
        # Create root element
        root = ET.Element('ComicInfo')
        root.set('xmlns', self.xmlns)
        
        # Basic issue information
        if comicvine_metadata.get('name'):
            title_elem = ET.SubElement(root, 'Title')
            title_elem.text = self.clean_text(comicvine_metadata['name'])
        
        if kapowarr_issue.get('issue_number'):
            number_elem = ET.SubElement(root, 'Number')
            number_elem.text = str(kapowarr_issue['issue_number'])
        
        # Date information - prefer store_date over cover_date for more accurate dates
        date_to_use = None
        if comicvine_metadata.get('store_date'):
            date_to_use = comicvine_metadata['store_date']
        elif comicvine_metadata.get('cover_date'):
            date_to_use = comicvine_metadata['cover_date']
        
        if date_to_use:
            try:
                date_obj = datetime.strptime(date_to_use, '%Y-%m-%d')
                
                year_elem = ET.SubElement(root, 'Year')
                year_elem.text = str(date_obj.year)
                
                month_elem = ET.SubElement(root, 'Month')
                month_elem.text = str(date_obj.month)
                
                day_elem = ET.SubElement(root, 'Day')
                day_elem.text = str(date_obj.day)
                
                # Also keep CoverDate for backward compatibility
                cover_date_elem = ET.SubElement(root, 'CoverDate')
                cover_date_elem.text = date_to_use
            except:
                # Fallback to just CoverDate if parsing fails
                cover_date_elem = ET.SubElement(root, 'CoverDate')
                cover_date_elem.text = date_to_use
        
        # Volume information
        if comicvine_metadata.get('volume', {}).get('name'):
            series_elem = ET.SubElement(root, 'Series')
            series_elem.text = comicvine_metadata['volume']['name']
        
        if comicvine_metadata.get('volume', {}).get('id'):
            volume_elem = ET.SubElement(root, 'Volume')
            volume_elem.text = str(comicvine_metadata['volume']['id'])
        
        # Description
        if comicvine_metadata.get('description'):
            summary_elem = ET.SubElement(root, 'Summary')
            summary_elem.text = self.clean_text(comicvine_metadata['description'])
        
        # Creator credits
        if comicvine_metadata.get('person_credits'):
            writer_elem = ET.SubElement(root, 'Writer')
            writers = [c for c in comicvine_metadata['person_credits'] if c.get('role') == 'writer']
            if writers:
                writer_elem.text = ', '.join([c['name'] for c in writers])
            
            penciller_elem = ET.SubElement(root, 'Penciller')
            pencillers = [c for c in comicvine_metadata['person_credits'] if c.get('role') == 'artist']
            if pencillers:
                penciller_elem.text = ', '.join([c['name'] for c in pencillers])
            
            inker_elem = ET.SubElement(root, 'Inker')
            inkers = [c for c in comicvine_metadata['person_credits'] if c.get('role') == 'inker']
            if inkers:
                inker_elem.text = ', '.join([c['name'] for c in inkers])
            
            colorist_elem = ET.SubElement(root, 'Colorist')
            colorists = [c for c in comicvine_metadata['person_credits'] if c.get('role') == 'colorist']
            if colorists:
                colorist_elem.text = ', '.join([c['name'] for c in colorists])
            
            letterer_elem = ET.SubElement(root, 'Letterer')
            letterers = [c for c in comicvine_metadata['person_credits'] if c.get('role') == 'letterer']
            if letterers:
                letterer_elem.text = ', '.join([c['name'] for c in letterers])
            
            cover_artist_elem = ET.SubElement(root, 'CoverArtist')
            cover_artists = [c for c in comicvine_metadata['person_credits'] if c.get('role') == 'cover']
            if cover_artists:
                cover_artist_elem.text = ', '.join([c['name'] for c in cover_artists])
            
            # Editors
            editors = [c for c in comicvine_metadata['person_credits'] if c.get('role') == 'editor']
            if editors:
                editor_elem = ET.SubElement(root, 'Editor')
                editor_elem.text = ', '.join([c['name'] for c in editors])
        
        # Character and team information
        if comicvine_metadata.get('character_credits'):
            characters = [c['name'] for c in comicvine_metadata['character_credits']]
            if characters:
                character_elem = ET.SubElement(root, 'Characters')
                character_elem.text = ', '.join(characters)
                
                # Set main character (first one) if available
                if characters:
                    main_character_elem = ET.SubElement(root, 'MainCharacterOrTeam')
                    main_character_elem.text = characters[0]
        
        if comicvine_metadata.get('team_credits'):
            teams = [c['name'] for c in comicvine_metadata['team_credits']]
            if teams:
                team_elem = ET.SubElement(root, 'Teams')
                team_elem.text = ', '.join(teams)
        
        # Story arc information
        if comicvine_metadata.get('story_arc_credits'):
            arcs = [c['name'] for c in comicvine_metadata['story_arc_credits']]
            if arcs:
                arc_elem = ET.SubElement(root, 'StoryArc')
                arc_elem.text = ', '.join(arcs)
        
        # Publisher (assuming DC Comics based on your example)
        publisher_elem = ET.SubElement(root, 'Publisher')
        publisher_elem.text = 'DC Comics'
        
        # Genre
        genre_elem = ET.SubElement(root, 'Genre')
        genre_elem.text = 'Superhero'
        
        # Language (using proper ISO format)
        language_elem = ET.SubElement(root, 'LanguageISO')
        language_elem.text = 'en-US'
        
        # Format (assuming standard comic format)
        format_elem = ET.SubElement(root, 'Format')
        format_elem.text = 'Digital'
        
        # Notes field for application info
        notes_elem = ET.SubElement(root, 'Notes')
        notes_elem.text = 'Metadata generated by turt using from ComicVine and Kapowarr data'
        
        # Web/URL references (standard ComicInfo field)
        if comicvine_metadata.get('site_detail_url'):
            web_elem = ET.SubElement(root, 'Web')
            web_elem.text = comicvine_metadata['site_detail_url']
        
        # Format the XML with proper indentation
        rough_string = ET.tostring(root, 'unicode')
        reparsed = minidom.parseString(rough_string)
        return reparsed.toprettyxml(indent="  ")
    
    def generate_xml_files(self, metadata_file: str, output_dir: str = "comic_info_xml"):
        """Generate ComicInfo.xml files for all issues in the metadata"""
        try:
            # Load metadata
            with open(metadata_file, 'r', encoding='utf-8') as f:
                metadata = json.load(f)
            
            # Create output directory
            os.makedirs(output_dir, exist_ok=True)
            
            print(f"Found {len(metadata)} issues to process")
            
            # Process each issue
            for comicvine_id, issue_data in metadata.items():
                try:
                    kapowarr_issue = issue_data.get('kapowarr_issue', {})
                    issue_number = kapowarr_issue.get('issue_number', 'Unknown')
                    series_name = kapowarr_issue.get('title', 'Unknown')
                    
                    print(f"Processing issue {issue_number}: {series_name}")
                    
                    # Generate XML content
                    xml_content = self.create_comic_info_xml(issue_data)
                    
                    # Create filename
                    safe_series = re.sub(r'[<>:"/\\|?*]', '_', series_name)
                    filename = f"Issue_{issue_number}_{safe_series}_ComicInfo.xml"
                    filepath = os.path.join(output_dir, filename)
                    
                    # Write XML file
                    with open(filepath, 'w', encoding='utf-8') as f:
                        f.write(xml_content)
                    
                    print(f"  Created: {filename}")
                    
                except Exception as e:
                    print(f"  Error processing issue {comicvine_id}: {e}")
                    continue
            
            print(f"\nXML generation complete! Files saved to: {output_dir}")
            
        except FileNotFoundError:
            print(f"Metadata file not found: {metadata_file}")
        except json.JSONDecodeError:
            print(f"Invalid JSON in metadata file: {metadata_file}")
        except Exception as e:
            print(f"Error processing metadata: {e}")

    def generate_issue_xml(self, metadata: dict, target_issue: dict, volume_details: dict) -> str:
        """Generate XML content for a specific issue
        
        Args:
            metadata: ComicVine metadata for the issue
            target_issue: Issue details from Kapowarr
            volume_details: Volume details from Kapowarr
            
        Returns:
            XML content as a string
        """
        # Create root element
        root = ET.Element('ComicInfo')
        root.set('xmlns', self.xmlns)
        
        # Basic issue information
        if metadata.get('name'):
            title_elem = ET.SubElement(root, 'Title')
            title_elem.text = self.clean_text(metadata['name'])
        
        if target_issue.get('issue_number'):
            number_elem = ET.SubElement(root, 'Number')
            number_elem.text = str(target_issue['issue_number'])
        
        # Volume information
        if metadata.get('volume', {}).get('name'):
            series_elem = ET.SubElement(root, 'Series')
            series_elem.text = metadata['volume']['name']
            
            volume_elem = ET.SubElement(root, 'Volume')
            volume_elem.text = metadata['volume']['name']
            
            alternate_series_elem = ET.SubElement(root, 'AlternateSeries')
            alternate_series_elem.text = metadata['volume']['name']
        
        # Issue count
        if volume_details.get('issue_count'):
            count_elem = ET.SubElement(root, 'Count')
            count_elem.text = str(volume_details['issue_count'])
            
            alternate_count_elem = ET.SubElement(root, 'AlternateCount')
            alternate_count_elem.text = str(volume_details['issue_count'])
        
        # Alternate number
        if target_issue.get('issue_number'):
            alternate_number_elem = ET.SubElement(root, 'AlternateNumber')
            alternate_number_elem.text = str(target_issue['issue_number'])
        
        # Description
        if metadata.get('description'):
            summary_elem = ET.SubElement(root, 'Summary')
            summary_elem.text = self.clean_text(metadata['description'])
        
        # Notes
        notes_elem = ET.SubElement(root, 'Notes')
        notes_elem.text = 'Processed by Comic Metadata Manager'
        
        # Date information - prefer store_date over cover_date for more accurate dates
        date_to_use = None
        if metadata.get('store_date'):
            date_to_use = metadata['store_date']
        elif metadata.get('cover_date'):
            date_to_use = metadata['cover_date']
        
        if date_to_use:
            try:
                date_obj = datetime.strptime(date_to_use, '%Y-%m-%d')
                
                year_elem = ET.SubElement(root, 'Year')
                year_elem.text = str(date_obj.year)
                
                month_elem = ET.SubElement(root, 'Month')
                month_elem.text = str(date_obj.month)
                
                day_elem = ET.SubElement(root, 'Day')
                day_elem.text = str(date_obj.day)
                
                # Also keep CoverDate for backward compatibility
                cover_date_elem = ET.SubElement(root, 'CoverDate')
                cover_date_elem.text = date_to_use
            except:
                # Fallback to just CoverDate if parsing fails
                cover_date_elem = ET.SubElement(root, 'CoverDate')
                cover_date_elem.text = date_to_use
        
        # Creator credits
        if metadata.get('person_credits'):
            # Writers
            writers = [c for c in metadata['person_credits'] if c.get('role') == 'writer']
            if writers:
                writer_elem = ET.SubElement(root, 'Writer')
                writer_elem.text = ', '.join([c['name'] for c in writers])
            
            # Pencillers
            pencillers = [c for c in metadata['person_credits'] if c.get('role') == 'penciler']
            if pencillers:
                penciller_elem = ET.SubElement(root, 'Penciller')
                penciller_elem.text = ', '.join([c['name'] for c in pencillers])
            
            # Inkers
            inkers = [c for c in metadata['person_credits'] if c.get('role') == 'inker']
            if inkers:
                inker_elem = ET.SubElement(root, 'Inker')
                inker_elem.text = ', '.join([c['name'] for c in inkers])
            
            # Colorists
            colorists = [c for c in metadata['person_credits'] if c.get('role') == 'colorist']
            if colorists:
                colorist_elem = ET.SubElement(root, 'Colorist')
                colorist_elem.text = ', '.join([c['name'] for c in colorists])
            
            # Letterers
            letterers = [c for c in metadata['person_credits'] if c.get('role') == 'letterer']
            if letterers:
                letterer_elem = ET.SubElement(root, 'Letterer')
                letterer_elem.text = ', '.join([c['name'] for c in letterers])
            
            # Cover artists
            cover_artists = [c for c in metadata['person_credits'] if c.get('role') == 'cover']
            if cover_artists:
                cover_artist_elem = ET.SubElement(root, 'CoverArtist')
                cover_artist_elem.text = ', '.join([c['name'] for c in cover_artists])
            
            # Editors
            editors = [c for c in metadata['person_credits'] if c.get('role') == 'editor']
            if editors:
                editor_elem = ET.SubElement(root, 'Editor')
                editor_elem.text = ', '.join([c['name'] for c in editors])
        
        # Publisher
        if metadata.get('publisher', {}).get('name'):
            publisher_elem = ET.SubElement(root, 'Publisher')
            publisher_elem.text = metadata['publisher']['name']
        
        # Imprint
        if metadata.get('imprint', {}).get('name'):
            imprint_elem = ET.SubElement(root, 'Imprint')
            imprint_elem.text = metadata['imprint']['name']
        
        # Genre
        if metadata.get('genres'):
            genres = [genre['name'] for genre in metadata['genres']]
            if genres:
                genre_elem = ET.SubElement(root, 'Genre')
                genre_elem.text = ', '.join(genres)
        
        # Web/URL references
        if metadata.get('site_detail_url'):
            web_elem = ET.SubElement(root, 'Web')
            web_elem.text = metadata['site_detail_url']
        
        # Page count
        if metadata.get('page_count'):
            page_count_elem = ET.SubElement(root, 'PageCount')
            page_count_elem.text = str(metadata['page_count'])
        
        # Language
        language_elem = ET.SubElement(root, 'LanguageISO')
        language_elem.text = 'en'
        
        # Format
        format_elem = ET.SubElement(root, 'Format')
        format_elem.text = 'Comic'
        
        # Age rating
        age_rating_elem = ET.SubElement(root, 'AgeRating')
        age_rating_elem.text = 'Unknown'
        
        # Manga
        manga_elem = ET.SubElement(root, 'Manga')
        manga_elem.text = 'No'
        
        # Black and white
        black_white_elem = ET.SubElement(root, 'BlackAndWhite')
        black_white_elem.text = 'No'
        
        # Scan information
        scan_info_elem = ET.SubElement(root, 'ScanInformation')
        scan_info_elem.text = 'Comic Metadata Manager'
        
        # Format the XML with proper indentation
        rough_string = ET.tostring(root, 'unicode')
        reparsed = minidom.parseString(rough_string)
        return reparsed.toprettyxml(indent="  ")

def main():
    """Main function to run the XML generator"""
    try:
        generator = ComicInfoXMLGenerator()
        
        # Get metadata file path
        metadata_file = input("Enter the path to the metadata JSON file: ").strip()
        if not metadata_file:
            print("Metadata file path cannot be empty")
            return
        
        if not os.path.exists(metadata_file):
            print(f"File not found: {metadata_file}")
            return
        
        # Get output directory
        output_dir = input("Enter output directory (or press Enter for default 'comic_info_xml'): ").strip()
        if not output_dir:
            output_dir = "comic_info_xml"
        
        # Generate XML files
        generator.generate_xml_files(metadata_file, output_dir)
        
    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    main()
