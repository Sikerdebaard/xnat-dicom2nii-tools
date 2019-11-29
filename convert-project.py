from converter import convert_project_dcm2nii, convert_project_sedi

# Inputs: general
xnat_url = 'https://xnat.bmia.nl/'
project_name = 'stwstrategyhn1'
tempfolder = '/media/martijn/DATA/tmp'
keyword = ''

# Convert all DICOMS (including RTStruct) to Nifti
convert_project_dcm2nii(project_name, xnat_url, tempfolder, keyword)

# Inputs: send to SEDI server. Currently set to the defaults
peer = '127.0.0.1'
port = 5000
ae_title = 'SEDIDICOM'

# Send all DICOMS (including RTStruct) to SEDI
convert_project_sedi(project_name, xnat_url, tempfolder, keyword,
                     peer, port, ae_title)
