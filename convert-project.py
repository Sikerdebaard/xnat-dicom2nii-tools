import xnat
import os
import sys

from glob import glob

from xnat.exceptions import XNATResponseError
from dcmrtstruct2nii import dcmrtstruct2nii

def download_subject(project, subject, datafolder, session):
    import os
    import shutil

    # Connect to XNAT
    subject = session.projects[project].subjects[subject]

    outdir = datafolder + '/{}'.format(subject.label)
    if not os.path.exists(outdir):
        os.makedirs(outdir)

    download_counter = 0

    for e in subject.experiments:
        resmap = {}
        experiment = subject.experiments[e]
        # NOTE: We only download the CT sessions, no PET scans
        if experiment.session_type is not None and '_CT' in experiment.session_type:  # some files in project don't have _CT postfix
            # NOTE: We only download the images, not the RTStruct file, which is a scan consisting of a single file
            for s in experiment.scans:
                scan = experiment.scans[s]
                print(("\tDownloading patient {}, experiment {}, scan {}.").format(subject.label, experiment.label,
                                                                                 scan.id))
                for res in scan.resources:
                    resource_label = scan.resources[res].label
                    resmap[resource_label] = scan
                    print(f'resource is {resource_label}')
                    scan.resources[res].download_dir(outdir)
                    download_counter += 1

    if download_counter > 0:
        print('Converting...')
        rtstruct_file = glob(outdir + '/*/scans/*/resources/secondary/files/*.dcm')[0]
        dicom_path = glob(outdir + '/*/scans/*/resources/DICOM/files/')[0]

        nii_output = outdir + '/nii'
        if not os.path.exists(nii_output):
            os.makedirs(nii_output)

        dcmrtstruct2nii(rtstruct_file, dicom_path, nii_output)

        nii_files = glob(outdir + '/nii/*.nii.gz')

        #assessment = 'NIFTI'
        resource_name = 'NIFTI'

        #xnat_assessment = session.classes.QcAssessmentData(parent=experiment, label=assessment)

        # try:
        #     resource = session.classes.ResourceCatalog(parent=xnat_assessment, label=resource)
        # except XNATResponseError as e:
        #     if not 'Specified resource already exists' in str(e):
        #         raise e
        #     shutil.rmtree(outdir)
        #     return True


        for file in nii_files:
            print(f'\t\tUploading {file}')
            try:
                if file.split('/')[-1].startswith('mask_'):
                    resource = put_resource(session, resmap['secondary'], resource_name)
                else:
                    resource = put_resource(session, resmap['DICOM'], resource_name)

                resource.upload(file, os.path.basename(file))
            except XNATResponseError as e:
                if not 'Specified resource already exists' in str(e):
                    raise e

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

def main():
    project_name = 'EMCDemo'

    # Connect to XNAT and retreive project
    session = xnat.connect('https://xnat.bmia.nl/')
    project = session.projects[project_name]

    # Create the data folder if it does not exist yet
    datafolder = ('/scratch/tphil/Data/{}').format(project_name)
    if not os.path.exists(datafolder):
        os.makedirs(datafolder)

    subjects_len = len(project.subjects)
    subjects_counter = 1
    for s in project.subjects:
        print(f'Working on subject {subjects_counter}/{subjects_len}')

        subjects_counter += 1

        # if not 'HN1067' in project.subjects[s].label:
        #     continue

        if not project.subjects[s].label.startswith('HN'):
            continue

        # subject = project.subjects[s]
        # print(s)
        download_subject(project_name, s, datafolder, session)

    # Disconnect the session
    session.disconnect()

    print('Done downloading!')


if __name__ == "__main__":
    main()
