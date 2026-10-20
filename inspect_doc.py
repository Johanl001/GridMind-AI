import zipfile
import xml.etree.ElementTree as ET

with zipfile.ZipFile('AIML FINAL REPORT.docx') as z:
    xml_content = z.read('word/document.xml')
    rels_content = z.read('word/_rels/document.xml.rels')

rtree = ET.fromstring(rels_content)
rid_map = {}
for rel in rtree:
    rid_map[rel.attrib['Id']] = rel.attrib.get('Target', '')

tree = ET.fromstring(xml_content)
for p in tree.iter('{http://schemas.openxmlformats.org/wordprocessingml/2006/main}p'):
    p_text = ''.join(p.itertext()).strip()
    blips = p.findall('.//{http://schemas.openxmlformats.org/drawingml/2006/main}blip')
    for b in blips:
        embed = b.attrib.get('{http://schemas.openxmlformats.org/officeDocument/2006/relationships}embed')
        print(f"Image {rid_map.get(embed)} near text: '{p_text[:60]}'")
