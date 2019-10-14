import xnat
import os
import sys
import shutil
from glob import glob

from xnat.exceptions import XNATResponseError
from dcmrtstruct2nii import dcmrtstruct2nii


def convert_subject(project, subject, datafolder, session):
    # Create output directory
    outdir = datafolder + '/{}'.format(subject.label)
    if not os.path.exists(outdir):
        os.makedirs(outdir)

    # Download all data and keep track of resources
    download_counter = 0
    resource_labels = list()
    for e in subject.experiments:
        resmap = {}
        experiment = subject.experiments[e]

        # FIXME: Need a way to smartly check whether we have a matching RT struct and image
        # Current solution: We only download the CT sessions, no PET / MRI / Other scans
        # Specific for STW Strategy BMIA XNAT projects

        if experiment.session_type is None:  # some files in project don't have _CT postfix
            print(f"\tSkipping patient {subject.label}, experiment {experiment.label}: type is not CT but {experiment.session_type}.")
            continue

        if '_CT' not in experiment.session_type:
            print(f"\tSkipping patient {subject.label}, experiment {experiment.label}: type is not CT but {experiment.session_type}.")
            continue

        for s in experiment.scans:
            scan = experiment.scans[s]
            print(("\tDownloading patient {}, experiment {}, scan {}.").format(subject.label, experiment.label,
                                                                             scan.id))
            for res in scan.resources:
                resource_label = scan.resources[res].label
                resmap[resource_label] = scan
                print(f'resource is {resource_label}')

                try:
                    scan.resources[res].download_dir(outdir)
                    resource_labels.append(resource_label)
                    download_counter += 1
                except XNATResponseError:
                    print("\t Resource empty, skipping.")
                    continue


    # Parse resources and throw warnings if they not meet the requirements
    subject_name = subject.label
    if download_counter == 0:
        print(f'[WARNING] Skipping subject {subject_name}: no (suitable) resources found.')
        return False

    if 'secondary' not in resource_labels:
        print(f'[WARNING] Skipping subject {subject_name}: no secondary resources found.')
        return False

    secondary_folder = glob(os.path.join(outdir, '*', 'scans', '*', 'resources', 'secondary', 'files'))[0]
    secondary_files = glob(os.path.join(secondary_folder, '*'))
    if len(secondary_files) == 0:
        print(f'[WARNING] Skipping subject {subject_name}: secondary resources is empty.')
        return False

    if 'DICOM' not in resource_labels:
        print(f'[WARNING] Skipping subject {subject_name}: no DICOM resource found.')
        return False

    dicom_path = glob(os.path.join(outdir, '*', 'scans', '*', 'resources', 'DICOM', 'files'))[0]
    DICOM_files = glob(os.path.join(dicom_path, '*'))
    if len(DICOM_files) == 0:
        print(f'[WARNING] Skipping subject {subject_name}: DICOM resource is empty.')
        return False

    # If resources are valid, apply nifti conversion
    print('Converting...')
    rtstruct_file = secondary_files[0]

    nii_output = os.path.join(outdir, 'nii')
    if not os.path.exists(nii_output):
        os.makedirs(nii_output)

    dcmrtstruct2nii(rtstruct_file, dicom_path, nii_output)

    nii_files = glob(os.path.join(outdir, 'nii', '*.nii.gz'))
    if len(nii_files) == 0:
        print(f"[WARNING] Conversion failed for subject {subject_name}: no Nifti's found. Skipping.")
        return False

    resource_name = 'NIFTI'
    for file in nii_files:
        print(f'\t\tUploading {file}')
        try:
            if file.split('/')[-1].startswith('mask_'):
                resource = put_resource(session, resmap['secondary'], resource_name)
            else:
                resource = put_resource(session, resmap['DICOM'], resource_name)

            resource.upload(file, os.path.basename(file))
        except XNATResponseError as e:
            if 'Specified resource already exists' not in str(e):
                raise enc

    # Remove output folder
    shutil.rmtree(outdir)

    return True


def put_resource(session, scan, label):
    try:
        resource = session.classes.ResourceCatalog(parent=scan, label=label)
    except XNATResponseError as e:
        if not 'Specified resource already exists' in str(e):
            raise e
        return scan.resources['NIFTI']
    return resource


def convert_project(project_name, xnat_url, tempfolder, keyword=''):

    # Connect to XNAT and retreive project
    session = xnat.connect(xnat_url)
    project = session.projects[project_name]

    # Create the data folder if it does not exist yet
    datafolder = os.path.join(tempfolder, 'XNAT2NII_' + project_name)
    if not os.path.exists(datafolder):
        os.makedirs(datafolder)

    subjects_len = len(project.subjects)
    subjects_counter = 1
    for s in range(0, subjects_len):
        s = project.subjects[s]
        print(f'Working on subject {subjects_counter}/{subjects_len}')

        subjects_counter += 1

        # if not 'HN1067' in project.subjects[s].label:
        #     continue

        if not s.label.startswith(keyword):
            continue

        # subject = project.subjects[s]
        # print(s)
        convert_subject(project_name, s, datafolder, session)

    # Disconnect the session
    session.disconnect()

    print('Done downloading!')
