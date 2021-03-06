from ..tools import display_html as _display


class PipeTemplate(object):
    """ Pipeline template class
    """

    @property
    def avail(self):
        pipes = [pipe[5:] for pipe in dir(self) if 'pipe_' in pipe]
        output = dict(zip(range(len(pipes)), pipes))
        return output


class T_Temporary_dataholder(PipeTemplate):
    def __init__(self, proc, tmpobj, surfix='func', n_thread='max'):
        """ Temporary data holder when for usage of data trimming in case user needs complex group organization from raw data
Author  : SungHo Lee(shlee@unc.edu)
Revised : Dec.11st.2017

Parameters:
    n_thread: int or str
        Set parallel processing, pynit pipeline use multi-threading to run parallel processing
        Please set to 1 if you use the linux virtual machine.
        (default: 'max')
    surfix  : str
        Surfix for output folder (default: 'func')
        """
        self.proc = proc
        self.tmpobj = tmpobj
        self.surfix = surfix
        self.n_thread = n_thread


class A_fMRI_preprocess(PipeTemplate):
    def __init__(self, proc, tmpobj, anat='anat', func='func', tr=None, tpattern=None, aniso=False,
                 cbv=None, ui=False, surfix='func', n_thread='max'):
        """Collection of preprocessing pipelines for Shihlab at UNC
Author  : SungHo Lee(shlee@unc.edu)
Revised : Dec.11st.2017

Parameters:
    anat    : str
        Path of anatomical images (default: 'anat')
        Set as None if anatomical images are not prepared (EPI template need to be provided)
    func    : str
        Path of functional images (default: 'func')
    tr      : int
        Temporal sampling time(sec) for a volume (default: None)
    tpattern: str
        Slice order code based on afni command '3dTshift' (default: None)
            alt+z = altplus   = alternating in the plus direction
            alt+z2            = alternating, starting at slice #1 instead of #0
            alt-z = altminus  = alternating in the minus direction
            alt-z2            = alternating, starting at slice #nz-2 instead of #nz-1
            seq+z = seqplus   = sequential in the plus direction
            seq-z = seqminus  = sequential in the minus direction
    aniso   : bool
        Set True if you use 2D anitotropic sliced image (default: False)
    cbv     : str
        Path of MION infusion image (default: False)
    ui      : bool
        UI supports (default: False)
    n_thread: int or str
        Set parallel processing, pynit pipeline use multi-threading to run parallel processing
        Please set to 1 if you use the linux virtual machine.
        (default: 'max')
    surfix  : str
        Surfix for output folder (default: 'func')
        """
        # Define attributes
        self.proc = proc
        self.func = func
        self.anat = anat
        self.tmpobj = tmpobj
        self.tr = tr
        self.tpattern = tpattern
        self.aniso = aniso
        self.cbv = cbv
        self.ui = ui
        self.surfix = surfix
        self.n_thread = n_thread

    def pipe_01_Brain_Mask_Preparation(self):
        """ Mask preparation step
        """
        # Mean image calculation (0)
        if self.cbv:
            self.proc.afni_MeanImgCalc(self.cbv, cbv=True, n_thread=self.n_thread, surfix=self.surfix)
        else:
            self.proc.afni_MeanImgCalc(self.func, n_thread=self.n_thread, surfix=self.surfix)
        # Mask preparation (1-anat, 2-func) or (1-func) if no anat
        if self.ui:
            self.proc.afni_MaskPrep(self.anat, 0, self.tmpobj, n_thread=self.n_thread, ui=True)
        else:
            self.proc.afni_MaskPrep(self.anat, 0, self.tmpobj, n_thread=self.n_thread)

    def pipe_02_Standard_Preprocessing(self):
        """ Standard preprocessing
        """
        # Update mask files (1-anat, 2-func) or (1-func) if no anat
        if not self.ui:
            if self.anat != None:
                self.proc.afni_PasteMask(0, 1, n_thread=self.n_thread)
                self.proc.afni_PasteMask(1, 2, n_thread=self.n_thread)
            else:
                self.proc.afni_PasteMask(0, 1, n_thread=self.n_thread)
        # Skull stripping (3-anat, 4-func) or (2-func if no anat)
        self.proc.afni_SkullStrip(self.anat, 0, n_thread=self.n_thread)
        if self.anat != None: # Dataset has anatomy image
            slicetime = 6
            motioncor = 7
            funcmask = 2
            # Coregistration (5)
            self.proc.afni_Coreg(3, 4, aniso=self.aniso, n_thread=self.n_thread, surfix=self.surfix)
        else: # Dataset doesn't have anatomy image
            slicetime = 3
            motioncor = 4
            funcmask = 1
        # Slice timing correction (6) or (2) if no anat
        if self.tr or self.tpattern:
            self.proc.afni_SliceTimingCorrection(self.func, tr=self.tr, tpattern=self.tpattern,
                                                 n_thread=self.n_thread, surfix=self.surfix)
        else:
            self.proc.afni_SliceTimingCorrection(self.func, n_thread=self.n_thread, surfix=self.surfix)
        # Motion correction (7) or (3) if no anat
        self.proc.afni_MotionCorrection(slicetime, 0, n_thread=self.n_thread, surfix=self.surfix)
        # Skull stripping all functional data (8) or (4) if no anat
        self.proc.afni_SkullStripAll(motioncor, funcmask, n_thread=self.n_thread, surfix=self.surfix)
        if self.anat != None: # Dataset has anatomy image
            # Apply coregistration transform matrix to all functional data (9)
            self.proc.afni_ApplyCoregAll(8, 5, n_thread=self.n_thread, surfix=self.surfix)
            if not self.aniso:
                # Align anatomy image to template space (10)
                self.proc.ants_SpatialNorm(3, self.tmpobj, surfix='anat')
                # Align functional images to template space (11)
                self.proc.ants_ApplySpatialNorm(9, 10, surfix=self.surfix)
            else:
                self.proc.afni_SpatialNorm(3, self.tmpobj, n_thread=self.n_thread, surfix='anat')
                self.proc.afni_ApplySpatialNorm(9, 10, n_thread=self.n_thread, surfix=self.surfix)
            if self.cbv:
                # Coregistration MION infusion image to anatomy image (12)
                self.proc.afni_ApplyCoregAll(self.cbv, 5, n_thread=self.n_thread, surfix='cbv')
                # Align MION infusion image to template space (13)
                if not self.aniso:
                    self.proc.ants_ApplySpatialNorm(12, 10, surfix='cbv')
                else:
                    self.proc.afni_ApplySpatialNorm(12, 10, n_thread=self.n_thread, surfix='cbv')
        else: # Dataset doesn't have anatomy image
            if not self.aniso:
                # Align mean-functional image to template space (5) if no anat
                self.proc.ants_SpatialNorm(2, self.tmpobj, surfix=self.surfix)
                # Align functional image to template space (6)
                self.proc.ants_ApplySpatialNorm(5, 6, surfix=self.surfix)
                if self.cbv:
                    # Align MION infusion image to template space (7)
                    self.proc.ants_ApplySpatialNorm(self.cbv, 5, surfix='cbv')
            else:
                # Align mean-functional image to template space (5) if no anat
                self.proc.afni_SpatialNorm(2, self.tmpobj, n_thread=self.n_thread, surfix=self.surfix)
                # Align functional image to template space (6)
                self.proc.afni_ApplySpatialNorm(5, 6, n_thread=self.n_thread, surfix=self.surfix)
                if self.cbv:
                    # Align MION infusion image to template space (7)
                    self.proc.afni_ApplySpatialNorm(self.cbv, 5, n_thread=self.n_thread, surfix='cbv')
        _display('The standard preprocessing pipeline have finished.')
        _display('Please check "group_organizer" methods to perform further analysis.')


class B_evoked_fMRI_analysis(PipeTemplate):
    def __init__(self, proc, tmpobj, paradigm=None, fwhm=0.5, thresholds=None, mask=None, cbv_param=None, crop=None,
                 option=None, ui=False, case=None, outliers=None, subject_wise=False, surfix='func', n_thread='max'):
        """Collection of GLM analysis pipelines for Shihlab at UNC.

To use this pipeline, you must use 'group_organizer' method of pipeline handler.

Examples:
    pipe.group_organizer(origin=0, target=1, step_id=11,
                         group_filters=dict(group1=[['sub-e01','sub-e02',...],[],dict(file_tag='task-first')],
                                            group2=[['sub-c01','sub-c02',...],[],dict(file_tag='task-second')]))
    Above code will organize two groups from 0th packages (A_fMRI_preprocess) to this packages that has
    'task-first' and 'task-second' in filename for each group respectivly.
    11th indexed steps on pipe.executed (from package no.0) will be used.

This pipeline performs first, spatial smoothing and then analyze individual GLM using
OLS(3dDeconvolve, AFNI) and REML(3dREMLfit).
If you set thresholds, it will generate individual level clusters based on those threshold value.
The final results of this pipeline is group one-sample t-test of evoked map (3dMEMA, AFNI) and extracted
time-courses data using the mask (Microsoft excel format)

Author  : SungHo Lee(shlee@unc.edu)
Revised : Nov.5th.2017

Parameters:
    paradigm    : list
        stimulation paradigm. dict(group1=[[onset timepoints], [model,[param]]], group2=[], ..)
        e.g. dict(group1=[[30, 100],['BLOCK',[10,1]]],
                  group2=[[...],[...,[...]],...)
    fwhm        : float
        Voxel Smoothness (mm)
    thresholds : list (default: None)
        Threshold for generating clusters [pval, num_of_voxels]
    mask        : path (default: None)
        ROIs mask for extracting timecourses
        if not provided, then generating cluster map using evoked responses
    cbv_param   : [echotime, number_of_volume_to_calc_average], list (default: None)
        parameters to calculate CBV, if this parameters are given, CBV correction will be calculated

    crop        : list [start, end]
        range that you want to crop the time-course data (default: None)
    option      : str
        option for ROIs extraction ('bilateral', 'merge', or 'contra') (default: None)
    ui          : bool
        UI supports (default: False)
    case        : str
        Set this if you want to try multiple cases (default: None)
        This parameter will be added as additional surfix next to the original surfix value
    subject_wise: bool
        Set this value as True if you want to apply subject level mask to extract timecourse data
        The subject level masks are estimated by subtract group mask from individual clustered map
        (default: False)
    outliers    : list [str,..]
        The option to exclude certain subject or files for group analysis, use specific keywords in the filename
        (default: None)
    n_thread: int or str
        Set parallel processing, pynit pipeline use multi-threading to run parallel processing
        Please set to 1 if you use the linux virtual machine.
        (default: 'max')
    surfix      : str
        folder surfix (default: 'func')
        """
        # Define attributes
        self.tmpobj = tmpobj
        self.proc = proc
        self.thresholds = thresholds
        self.paradigm = paradigm
        self.cbv_param = cbv_param
        self.crop = crop
        self.fwhm = str(fwhm)
        self.option = option
        self.outliers = outliers
        self.mask = mask
        self.case = case
        self.subject_wise = subject_wise
        self.ui = ui
        self.surfix = surfix
        self.n_thread = n_thread
        # self.update()

    def pipe_01_GLM_analysis(self):
        if self.case:
            surfix = "{}_{}".format(self.surfix, self.case)
        else:
            surfix = self.surfix
        # Spatial smoothing (1)
        self.proc.afni_SpatialSmoothing(0, fwhm=self.fwhm, tmpobj=self.tmpobj, surfix=surfix,
                                        n_thread=self.n_thread)
        # Perform GLM analysis (2: GLM, 3: REMLfit)
        self.proc.afni_GLManalysis(1, self.paradigm, clip_range=self.crop,
                                   surfix=surfix, n_thread=self.n_thread)

    def pipe_02_GroupAverage(self):
        if self.case:
            surfix = "{}_{}".format(self.surfix, self.case)
        else:
            surfix = self.surfix
        # Calculate group average activity map (one-sample ttest)
        step = [step for step in self.proc.steps if self.surfix in step and 'REMLfit' in step][0]
        self.proc.afni_GroupAverage(step, outliers=self.outliers, surfix=surfix)

    def pipe_03_Extract_Timecourse(self):
        # Check if the image modality is CBV
        if self.cbv_param:
            cbv_id = 0
        else:
            cbv_id = False
        # Check threshold
        if not self.thresholds:
            self.thresholds = [None, None]
        # Check if the surfix is extended by case argument
        if self.case:
            surfix = "{}_{}".format(self.surfix, self.case)
            fullts = "fullts_{}".format(self.case)
        else:
            surfix = self.surfix
            fullts = "fullts"
        # Check if mask image is provided.
        if self.mask:
            mask = self.mask
            if self.subject_wise:
                step = [step for step in self.proc.steps if self.surfix in step and 'REMLfit' in step][0]
                clst = self.proc.afni_ClusterMap(step, 1, pval=self.thresholds[0], clst_size=self.thresholds[1],
                                                 surfix=surfix, n_thread=self.n_thread)
                mask = self.proc.afni_EstimateSubjectROIs(clst['mask'], mask, surfix=surfix)
        else:
            mask = self.tmpobj
        # Check if the crop range parameter is assigned
        if self.crop:
            total = [step for step in self.proc.steps if fullts in step and 'ExtractROIs' in step]
            if len(total):
                pass
            else:
                if not self.subject_wise:
                    self.proc.afni_ROIStats(1, mask, cbv=cbv_id, cbv_param=self.cbv_param, n_thread=self.n_thread,
                                            surfix=fullts)
                else:
                    step = [step for step in self.proc.steps if surfix in step and 'SubjectROIs' in step][0]
                    self.proc.afni_ROIStats(1, step, cbv=cbv_id, cbv_param=self.cbv_param, label=self.mask,
                                            n_thread=self.n_thread, surfix=fullts)
        if not self.subject_wise:
            # If mask given, extract timecourse using the given mask
            self.proc.afni_ROIStats(1, mask, cbv=cbv_id, cbv_param=self.cbv_param, clip_range=self.crop,
                                    option=self.option, n_thread=self.n_thread, surfix=surfix)
        # Extract timecourse using the mask you generated at step1
        else:
            step = [step for step in self.proc.steps if surfix in step and 'SubjectROIs' in step][0]
            self.proc.afni_ROIStats(1, step, clip_range=self.crop, option=self.option, label=self.mask,
                                    cbv_param=self.cbv_param, surfix=surfix, n_thread=self.n_thread, cbv=cbv_id)


class C_resting_state_fMRI_analysis(PipeTemplate):
    def __init__(self, proc, tmpobj, fwhm=None, dt=None, bpass=None, mask=None, ReHo_NN=3, use_PCA=True, FDR=True,
                 ort=None, ort_filter=None, surfix='func', n_thread='max'):
        """Collection of resting-state fMRI analysis pipeline for Shihlab at UNC

To use this pipeline, you must use 'group_organizer' method of pipeline handler.
Also 'optional_filters' need to be used while you organize group.

Examples:
    pipe.group_organizer(origin=0, target=2, step_id=11,
        s (A_fMRI_preprocess) to this package
    and the Preprocessed files that has 'task-rs' as filename in the 11th indexed steps
    will be used.
    The 'option filter' will collect the motion paramater files from 7th indexed step folder,
    which has '.1D' as extension but not has 'aff12'.

This pipeline performs rest of the preprocessing step for resting-state data, includes bandpass filter,
regression(nuisance, motion parameter), de-trending, and spatial smoothing (using 3dTproject, AFNI).
This pipeline is currently under development, so until the pipeline is stabilized, please use this for
preprocessing perpose only.

Author  : SungHo Lee(shlee@unc.edu)
Revised : Nov.5th.2017

Parameters:
    fwhm        : float
        Voxel Smoothness (mm)
    dt          : int
    bpass       : list [lowFHz, highFHz]
        Banspass filters (Defualt=None)
    ort         : str, list or dict
        index of the step id has regressor
    ort_filter  : filter, list of filter, dict(key=filter)
        the filters for ort, multiple filter can be performed
    ui          : bool
        UI supports (default: False)
    surfix      : str
        folder surfix (default: 'func')
        """
        # Define attributes
        self.tmpobj = tmpobj
        self.proc = proc
        self.bpass = bpass
        self.dt = dt
        self.fwhm = str(fwhm)
        self.ort = ort
        self.mask = mask
        self.NN = ReHo_NN
        self.ort_filter = ort_filter
        self.pca = use_PCA
        self.fdr = FDR
        self.surfix = surfix
        self.n_thread = n_thread
        # self.update()

    def pipe_01_FilteringWithoutQA(self):
        if self.mask is None:
            mask = str(self.tmpobj.mask.path)
        else:
            mask = self.mask
        # Temporal Processing (1)
        self.proc.nsp_SignalProcessing(0, mask=mask, param=self.ort, param_filter=self.ort_filter,
                                       dt=self.dt, band=self.bpass, n_thread=self.n_thread)
        # Spatial smoothing (2)
        self.proc.afni_SpatialSmoothing(1, self.fwhm, mask=mask, surfix='func', n_thread=1)

    def pipe_02_FilteringWithQA(self):
        if self.mask is None:
            mask = str(self.tmpobj.mask.path)
        else:
            mask = self.mask
        # Temporal Processing (1)
        self.proc.nsp_SignalProcessing(0, mask=mask, param=self.ort, param_filter=self.ort_filter,
                                       dt=self.dt, band=self.bpass, n_thread=self.n_thread)
        # Baseline quality (2)
        self.proc.nsp_QualityControl(0, mask=mask, mparam=0, surfix='Pre', n_thread=self.n_thread)

        # Post regression quality (3)
        self.proc.nsp_QualityControl(1, mask=mask, mparam=0, surfix='Post_regression', n_thread=self.n_thread)

        # DataType Correction (4)
        self.proc.afni_UpdateDataType(1, n_thread=self.n_thread)

        # Spatial smoothing (5)
        self.proc.afni_SpatialSmoothing(4, self.fwhm, mask=mask, surfix='func', n_thread=1)

        # Post smoothing quality (6)
        self.proc.nsp_QualityControl(5, mask=mask, mparam=0, surfix='Post_smoothing', n_thread=self.n_thread)

    def pipe_03_EstimateRestingstateParameters(self):
        step = sorted([step for step in self.proc.steps if self.surfix in step and 'SpatialSmoothing' in step])[0]
        if self.mask is None:
            mask = str(self.tmpobj.mask.path)
        else:
            mask = self.mask
        # ALFF (6?)
        self.proc.nsp_ALFF(step, mask=mask, dt=self.dt, band=self.bpass, surfix='func', n_thread=self.n_thread)

        # ReHo (7?)
        self.proc.nsp_ReHo(step, mask=mask, NN=self.NN, surfix='func', n_thread=self.n_thread)

    def pipe_04_RoiBasedConnectivityAnalysis(self):
        step = sorted([step for step in self.proc.steps if self.surfix in step and 'SpatialSmoothing' in step])[0]

        if self.mask is None:
            mask = str(self.tmpobj.mask.path)
        else:
            mask = self.mask
        # ROI-based whole brain connectivity (6 or 8)
        self.proc.nsp_ROIbasedConnectivity(step, tmpobj=self.tmpobj, mask=mask,
                                           use_PCA=self.pca, FDR=self.fdr, surfix='func', n_thread=self.n_thread)
        _display('RestingState Analysis pipeline is Done.')
        _display('Group statistic is not ready, please perform separately.')

