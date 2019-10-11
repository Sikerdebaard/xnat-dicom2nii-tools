from converter import convert_project

# Inputs
xnat_url = 'https://xnat.bmia.nl/'
project_name = 'EMCDemo'
tempfolder = '/media/martijn/DATA/tmp'
keyword = ''

convert_project(project_name, xnat_url, tempfolder, keyword)
