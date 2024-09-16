import os
import re
import json
import json5

def process_callout(match):
  type = re.search(r'type\s*=\s*"(\w+)"', match.group(1))
  emoji = re.search(r'emoji\s*=\s*"([^"]+)"', match.group(1))
  content = '\n> '.join(match.group(2).split('\n'))
    
  type_str = type.group(1) if type else ""
  emoji_str = emoji.group(1) if emoji else ""
  
  return f"> {emoji_str} {type_str} \n> \n> {content}\n"

def process_iframe(match):
  src = re.search(r'src="([^"]+)"', match.group(0))
  if src:
    url = src.group(1)
    if 'youtube.com' in url or 'youtu.be' in url:
      # For YouTube links, use the video title as link text
      return f'[Watch Video]({url})'
    else:
      # For other links, use a generic text
      return f'[View Content]({url})'
  return ''  # Return empty string if no src found

def process_tabs(match):
  items = re.search(r'items *= *\{(\[.*?\])\}', match.group(1))
  if items:
    items_list = json5.loads(items.group(1))
    tabs_content = re.findall(r'<Tab>(.*?)</Tab>', match.group(0), re.DOTALL)
    result = []
    for item, content in zip(items_list, tabs_content):
      content = content.strip()
      content = re.sub(r'\n', '\n  ', content)
      result.append(f"- {item}\n  {content}")
    return '\n'.join(result)
  return ''

def process_screenshot(match, screenshots):
  src = match.group(1)
  alt = match.group(2)
  return f"![{alt}]({screenshots[src]})"

def process_file(file_path, base_path, level):
  with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()
  
  screenshots = {}
  
  # log screenshots
  import_matches = re.findall(r"import\s+(\w+)\s+from\s+'([^']+)'", content)
  for var_name, path in import_matches:
    screenshots[var_name] = os.path.relpath(os.path.join(os.path.dirname(file_path), path), base_path)
    
  # Remove import statements
  content = re.sub(r"\n+import\s+.*?\s+from\s+'[^']*'$", '', content, flags=re.MULTILINE)
    
  # Process callouts
  content = re.sub(r'<Callout([^>]*)>(.*?)<\/Callout>', process_callout, content, flags=re.DOTALL)
  
  # Process iframes
  content = re.sub(r'<iframe[^>]+?(>.*?</iframe>|/>)', process_iframe, content, flags=re.DOTALL)
  
    # Process tabs
  content = re.sub(r'<Tabs([^>]*)>(.*?)</Tabs>', process_tabs, content, flags=re.DOTALL)
  
  # Remove ContentFileNames tags
  content = re.sub(r'<ContentFileNames[^>]*?/>', '', content)
  
  # Process image paths
  def replace_image_path(match):
    img_path = match.group(1)
    if not img_path.startswith(('http://', 'https://', '/')):
      rel_path = os.path.relpath(os.path.join(os.path.dirname(file_path), img_path), base_path)
      return f'![]({rel_path})'
    return match.group(0)
    
  content = re.sub(r'!\[.*?\]\((.*?)\)', replace_image_path, content)
    
  # Adjust heading levels
  content = re.sub(r'(\n*---)?(\n{0,2})\n*(#+) ', rf"\2{'#'*level}\3 ", content, flags=re.MULTILINE)
    
  return content

def process_directory(directory, base_path, level):
  output = []
  meta_file = os.path.join(directory, '_meta.en.json')
    
  if os.path.exists(meta_file):
    with open(meta_file, 'r', encoding='utf-8') as f:
      meta_data = json.load(f)
  else:
    meta_data = {}
    
  for key in meta_data.keys():
    file_path = os.path.join(directory, f"{key}.en.mdx")
    if os.path.exists(file_path):
      processed_content = process_file(file_path, base_path, level)
      output.append(processed_content)
        
    subdir_path = os.path.join(directory, key)
    if os.path.isdir(subdir_path):
      subdir_content = process_directory(subdir_path, base_path, level + 1)
      output.append(subdir_content)
    
  # # Process any remaining .en.mdx files not listed in _meta.en.json
  # for file in os.listdir(directory):
  #   if file.endswith('.en.mdx') and file[:-7] not in meta_data:
  #     file_path = os.path.join(directory, file)
  #     processed_content = process_file(file_path, base_path, level)
  #     output.append(processed_content)
    
  return '\n\n'.join(output)

def process_nextra_project(project_path):
  return process_directory(project_path+"/pages", project_path, 0)

output_content = process_nextra_project("./")

with open('output.md', 'w', encoding='utf-8') as f:
  f.write(output_content)
