import sys
import xml.etree.ElementTree as ET

def clean_urdf():
    try:
        # Read from stdin
        xml_content = sys.stdin.read()
        
        # Parse XML
        # This automatically handles comments (they are not preserved by default in ElementTree)
        root = ET.fromstring(xml_content)
        
        # Convert back to string
        # encoding='unicode' ensures it returns a string, method='xml' keeps it standard
        clean_xml = ET.tostring(root, encoding='unicode', method='xml')
        
        # Remove XML declaration if ElementTree added it (it usually doesn't with default settings but to be safe)
        if clean_xml.startswith('<?xml'):
            clean_xml = clean_xml.split('?>', 1)[1]
            
        # Remove newlines and extra spaces to make it a single line
        clean_xml = " ".join(clean_xml.split())
        
        print(clean_xml)
        
    except Exception as e:
        # In case of error, print original content to avoid breaking the pipeline completely,
        # verifying likely failed anyway but at least we see output.
        # Or print error to stderr.
        sys.stderr.write(f"Error cleaning URDF: {e}\n")
        # Ensure we output something valid or exit with error
        sys.exit(1)

if __name__ == "__main__":
    clean_urdf()