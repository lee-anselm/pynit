import os
import itertools
import pickle
import pandas as pd
import copy as ccopy
from ..tools import messages
from ..tools import methods


def mk_main_folder(prj):
    """
    Initiating project sub-folders\
    """
    methods.mkdir(os.path.join(prj.path, prj.ds_type[0]),
                  os.path.join(prj.path, prj.ds_type[1]),
                  os.path.join(prj.path, prj.ds_type[2]))


def check_arguments(args, residuals, reference):
    """
    This method retrieves the value in the 'reference' from the 'args',
    removes the corresponding value from the input 'residuals' arguments,
    and returns these values and the remaining residuals argument.
    """
    try:
        retrieved = [arg for arg in args if arg in reference]
    except:
        retrieved = []
    residuals = list(residuals)
    if len(retrieved):
        for comp in retrieved:
            if comp in residuals:
                residuals.remove(comp)
    return list(set(retrieved)), list(set(residuals))


def parsing_datatree(path, ds_type, idx):
    """
    This methods parsing the data tree from the given path
    """
    empty_prj = False
    single_session = False
    df = pd.DataFrame()
    for f in os.walk(os.path.join(path, ds_type[idx])):
        if f[2]:
            import re
            flist = [fname for fname in f[2] if not re.match(r'^[.].+', fname)]
            # print(flist)
            for filename in flist:
                row = pd.Series(methods.path_splitter(os.path.relpath(f[0], path)))
                # if row[0] == ds_type[2]:
                #     pass
                # else:
                row['Filename'] = filename
                row['Abspath'] = os.path.join(f[0], filename)
                # df = df.append(pd.DataFrame([row]), ignore_index=True)
                df = df.append(pd.DataFrame([row]), ignore_index=True, sort=True)
    if 1 not in df.columns:
        empty_prj = True
    elif not len(df):
        empty_prj = True
    else:
        if idx == 0:
            if len(df.columns) is 5:
                single_session = True
        elif idx == 1:
            if len(df.columns) is 6:
                single_session = True
        elif idx == 2:
            if len(df.columns) is 6:
                single_session = True
        columns = update_columns(idx, single_session)
        df = df.rename(columns=columns)
    if empty_prj:
        return pd.DataFrame(), single_session, empty_prj
    else:
        return df.sort_values('Abspath'), single_session, empty_prj


def initial_filter(df, data_class, exts):
    """
    Filtering out only selected file type in the project folder
    """
    if data_class:
        if not isinstance(data_class, list):
            data_class = [data_class]
        try:
            df = df[df['DataClass'].isin(data_class)]
        except:
            pass #logging function
    if exts:
        df = df[df['Filename'].str.contains('|'.join([r"{ext}$".format(ext=ext) for ext in exts]))]
    columns = df.columns
    return df.reset_index()[columns]


def update_columns(idx, single_session):
    """
    Update name of columns according to the set Dataclass
    """
    if idx == 0:
        if single_session:
            subject, session, dtype = (1, 3, 2)
        else:
            subject, session, dtype = (1, 2, 3)
        columns = {0: 'DataClass', subject: 'Subject', session: 'Session', dtype: 'DataType'}
    elif idx == 1:
        columns = {0: 'DataClass', 1: 'Pipeline', 2: 'Step', 3: 'Subject', 4: 'Session'}
    elif idx == 2:
        # columns = {0: 'DataClass', 1: 'Pipeline', 2: 'Report'}
        columns = {0: 'DataClass', 1: 'Pipeline', 2: 'Report', 3: 'Subject', 4: 'Session'}
    else:
        columns = {0: 'DataClass'}
    return columns


def reorder_columns(idx, single_session):
    """
    Reorder the name of columns
    """
    if idx == 0:
        if single_session:
            return ['Subject', 'DataType', 'Filename', 'Abspath']
        else:
            return ['Subject', 'Session', 'DataType', 'Filename', 'Abspath']
    elif idx == 1:
        if single_session:
            return ['Pipeline', 'Step', 'Subject', 'Filename', 'Abspath']
        else:
            return ['Pipeline', 'Step', 'Subject', 'Session', 'Filename', 'Abspath']
    elif idx == 2:
        if single_session:
            return ['Pipeline', 'Report', 'Subject', 'Filename', 'Abspath']
        else:
            return ['Pipeline', 'Report', 'Subject', 'Session', 'Filename', 'Abspath']
        # return ['Pipeline', 'Report', 'Filename', 'Abspath']
    else:
        return None


class Project(object):
    """
    Project handler
    """

    def __init__(self, project_path, **kwargs):
        """Load and initiate the project

        :param project_path: str, Path of particular project
        :param ds_ref: str, Reference of data structure (default: 'NIRAL')
        :param img_format: str, Reference img format (default: 'NifTi-1')
        :param kwargs: dict, key arguments for options
        """

        # Define default attributes
        self.single_session = False             # True if project has single session
        self.__empty_project = False            # True if project folder is empty
        self.__filters = [None] * 6
        # Each values are represented subject, session, dtype(or pipeline), step(or results) file_tags, ignores

        self.__path = os.path.abspath(project_path)

        # Set internal objects
        self.__df = pd.DataFrame()

        # Default definition of image format and data structure
        self.img_ext = ['.nii', '.nii.gz']
        self.ds_type = ['Data', 'Processing', 'Results']

        # Define default filter values
        self.__dc_idx = 0                       # Dataclass index
        self.__ext_filter = self.img_ext        # File extension
        self.__residuals = None

        # Generate folders for dataclasses
        mk_main_folder(self)

        # self._logger = methods.get_logger(self.__path, 'Project')
        # Scan project folder
        dc_idx = []
        for i in range(3):
            self.__dc_idx = i
            self.scan_prj()
            self.apply()
            if not self.__empty_project:
                dc_idx.append(i)
        if dc_idx:
            self.__dc_idx = max(dc_idx)
            self.scan_prj()
            self.apply()

    @property
    def df(self):
        """Dataframe for handling data structure

        :return: pandas.DataFrame
        """
        columns = self.__df.columns
        return self.__df.reset_index()[columns]

    @property
    def path(self):
        """Project path

        :return: str, path
        """
        return self.__path

    @property
    def dataclass(self):
        """Dataclass index

        :return: int, index
        """
        return self.ds_type[self.__dc_idx]

    @dataclass.setter
    def dataclass(self, idx):
        """Setter method for dataclass

        :param idx: int, index of dataclass
        :return: None
        """
        if idx in range(3):
            self.__dc_idx = idx
            self.reset()
            self.apply()
        else:
            methods.raiseerror(messages.Errors.InputDataclassError, 'Wrong dataclass index.')

    @property
    def subjects(self):
        return self.__subjects

    @property
    def sessions(self):
        return self.__sessions

    @property
    def dtypes(self):
        return self.__dtypes

    @property
    def pipelines(self):
        return self.__pipelines

    @property
    def steps(self):
        return self.__steps

    @property
    def results(self):
        return self.__results

    @property
    def filters(self):
        return self.__filters

    @property
    def summary(self):
        return self.__summary()

    @property
    def ext(self):
            return self.__ext_filter

    @ext.setter
    def ext(self, value):
        if type(value) == str:
            self.__ext_filter = [value]
        elif type(value) == list:
            self.__ext_filter = value
        elif not value:
            self.__ext_filter = None
        else:
            methods.raiseerror(messages.Errors.InputTypeError,
                               'Please use correct type for input.')
        self.reset()
        self.apply()

    @property
    def ref_exts(self, type='all'):
        """Reference extention handler

        :param type: str, Choose one of 'all', 'img' or 'txt'
        :return: list, list of extensions
        """
        img_ext = self.img_ext
        txt_ext = ['.xls', '.xlsx', '.csv', '.tsv', '.json']
        all_ext = img_ext+txt_ext
        if type in ['all', 'img', 'txt']:
            if type == 'all':
                output = all_ext
            elif type == 'img':
                output = img_ext
            elif type == 'txt':
                output = txt_ext
            else:
                output = None
            return list(itertools.chain.from_iterable(output))
        else:
            methods.raiseerror(messages.Errors.InputTypeError,
                               "only one of the value in ['all'.'img'.'txt'] is available for type.\n")

    def reload(self):
        """Reload dataset

        :return: None
        """
        self.reset(rescan=True)
        self.apply()

    def reset(self, rescan=False, verbose=False):
        """Reset DataFrame

        :param rescan: boolean, Choose if you want to re-scan all dataset
        :param verbose: boolean
        :return: None
        """

        if rescan:
            idx = int(self.__dc_idx)
            for i in range(2):
                self.__dc_idx = i+1
                self.scan_prj()
                if self.__empty_project:
                    if verbose:
                        print("Dataclass '{}' is Empty".format(self.ds_type[self.__dc_idx]))
            self.__dc_idx = idx
            self.scan_prj()
        else:
            prj_file = os.path.join(self.__path, self.ds_type[self.__dc_idx], '.class_dataframe')
            try:
                with open(prj_file, 'r') as f:
                    self.__df = pickle.load(f)
                if self.__dc_idx == 0:
                    if self.__empty_project:
                        pass
                    else:
                        if len(self.__df.columns) == 4:
                            self.single_session = True
                        else:
                            self.single_session = False
                else:
                    if self.__empty_project:
                        pass
                    else:
                        if len(self.__df.columns) == 5:
                            self.single_session = True
                        else:
                            self.single_session = False
            except:
                self.scan_prj()
        if len(self.__df):
            self.__empty_project = False

    def save_df(self, dc_idx):
        """Save Dataframe to pickle file

        :param dc_idx: idx, index in range(3)
        :return: None
        """
        dc_df = os.path.join(self.__path, self.ds_type[dc_idx], '.class_dataframe')
        if os.path.exists(dc_df):
            os.remove(dc_df)
        with open(dc_df, 'wb') as f:
            pickle.dump(self.__df, f, protocol=pickle.HIGHEST_PROTOCOL)

    def reset_filters(self, ext=None):
        """Reset filter - Clear all filter information and extension

        :param ext: str, Filter parameter for file extension
        :return: None
        """
        self.__filters = [None] * 6
        if not ext:
            self.ext = self.img_ext
        else:
            self.ext = ext

    def scan_prj(self):
        """Reload the Dataframe based on current set data class and extension

        :return: None
        """
        # Parsing command works
        self.__df, self.single_session, empty_prj = parsing_datatree(self.path, self.ds_type, self.__dc_idx)
        # print(self.__df)
        if not empty_prj:
            self.__df = initial_filter(self.__df, self.ds_type, self.ref_exts)
            if len(self.__df):
                self.__df = self.__df[reorder_columns(self.__dc_idx, self.single_session)]
                self.__empty_project = False
            else:
                self.__empty_project = True
            self.__update()
        else:
            self.__empty_project = True
        try:
            self.save_df(self.__dc_idx)
        except:
            pass

    def set_filters(self, *args, **kwargs):
        """Set filters

        :param args: str[, ], String arguments regarding hierarchical data structures
        :param kwargs: key=value pair[, ], Key and value pairs for the filtering parameter on filename
            :subparam file_tag: str or list of str, Keywords of interest for filename
            :subparam ignore: str or list of str, Keywords of neglect for filename
        :return: None
        """
        self.reset_filters(self.ext)
        pipe_filter = None
        if kwargs:
            for key in kwargs.keys():
                if key == 'dataclass':
                    self.dataclass = kwargs['dataclass']
                elif key == 'ext':
                    self.ext = kwargs['ext']
                elif key == 'file_tag':
                    if type(kwargs['file_tag']) == str:
                        self.__filters[4] = [kwargs['file_tag']]
                    elif type(kwargs['file_tag']) == list:
                        self.__filters[4] = kwargs['file_tag']
                    else:
                        methods.raiseerror(messages.Errors.InputTypeError,
                                                 'Please use correct input type for FileTag')
                elif key == 'ignore':
                    if type(kwargs['ignore']) == str:
                        self.__filters[5] = [kwargs['ignore']]
                    elif type(kwargs['ignore']) == list:
                        self.__filters[5] = kwargs['ignore']
                    else:
                        methods.raiseerror(messages.Errors.InputTypeError,
                                                 'Please use correct input type for FileTag to ignore')
                else:
                    methods.raiseerror(messages.Errors.KeywordError,
                                             "'{key}' is not correct kwarg")
        else:
            pass
        if args:
            residuals = list(set(args))
            if self.subjects: # If subjects are assigned already
                subj_filter, residuals = check_arguments(args, residuals, self.subjects)
                # print(subj_filter)
                if self.__filters[0]: # Subject filter
                    self.__filters[0].extend(subj_filter)
                else:
                    self.__filters[0] = subj_filter[:]
                if not self.single_session: # If multi-session project
                    sess_filter, residuals = check_arguments(args, residuals, self.sessions)
                    if self.__filters[1]: # Session filter
                        self.__filters[1].extend(sess_filter)
                    else:
                        self.__filters[1] = sess_filter[:]
                else:
                    self.__filters[1] = None
            else: # If no subjects are detected in this project, pass... (residual is not in subject and session)
                self.__filters[0] = None
                self.__filters[1] = None

            if self.__dc_idx == 0: # if dataclass is 0
                if self.dtypes: # check if residual arguments is parts of datatype (anat, func, or dti...)
                    dtyp_filter, residuals = check_arguments(args, residuals, self.dtypes)
                    if self.__filters[2]: # Datatype filter
                        self.__filters[2].extend(dtyp_filter)
                    else:
                        self.__filters[2] = dtyp_filter[:]
                else:
                    self.__filters[2] = None
                self.__filters[3] = None

            elif self.__dc_idx == 1:
                if self.pipelines:
                    pipe_filter, residuals = check_arguments(args, residuals, self.pipelines)
                    if self.__filters[2]:
                        self.__filters[2].extend(pipe_filter)
                    else:
                        self.__filters[2] = pipe_filter[:]
                else:
                    self.__filters[2] = None
                if self.steps:
                    step_filter, residuals = check_arguments(args, residuals, self.steps)
                    if self.__filters[3]:
                        self.__filters[3].extend(step_filter)
                    else:
                        self.__filters[3] = step_filter
                else:
                    self.__filters[3] = None
            else:
                if self.pipelines:
                    pipe_filter, residuals = check_arguments(args, residuals, self.pipelines)
                    if self.__filters[2]:
                        self.__filters[2].extend(pipe_filter)
                    else:
                        self.__filters[2] = pipe_filter[:]
                else:
                    self.__filters[2] = None
                if self.results:
                    rslt_filter, residuals = check_arguments(args, residuals, self.results)
                    if self.__filters[3]:
                        self.__filters[3].extend(rslt_filter)
                    else:
                        self.__filters[3] = rslt_filter[:]
                else:
                    self.__filters[3] = None

            if len(residuals):
                if self.dataclass == self.ds_type[1]:
                    if len(pipe_filter) == 1:
                        dc_path = os.path.join(self.path, self.dataclass, pipe_filter[0])
                        processed = os.listdir(dc_path)
                        if len([step for step in processed if step in residuals]):
                            # self._logger.debug('set_filters::Wrong filter(s)-{}'.format(residuals))
                            methods.raiseerror(messages.Errors.NoFilteredOutput,
                                               'Cannot find any results from [{residuals}]\n'
                                               '\t\t\tPlease take a look if you had applied correct filter inputs'
                                               ''.format(residuals=residuals))
                    else:
                        if not os.path.exists(os.path.join(self.path, self.dataclass, residuals[0])):
                            # Unexpected error
                            # self._logger.debug('set_filters::Exception on residual-{}'.format(residuals))
                            # self._logger.debug('set_filters::filters - {}, {}'.format(args, kwargs))
                            methods.raiseerror(messages.Errors.NoFilteredOutput,
                                               'Uncertain exception occured, please report to Author (shlee@unc.edu)')
                        else:
                            # When Processing folder is empty
                            self.__filters[2] = residuals
                else:
                    # self._logger.debug('set_filters::Wrong filter(s)-{}'.format(residuals))
                    methods.raiseerror(messages.Errors.NoFilteredOutput,
                                       'Wrong filter input:{residuals}'.format(residuals=residuals))
            else:
                self.__residuals = None

    def apply(self):
        """Applying all filters to current dataframe

        :return: None
        """
        self.__df = self.applying_filters(self.__df)
        self.__update()

    def applying_filters(self, df):
        """Applying current filters to the given dataframe

        :param df: pandas.DataFrame
        :return: pandas.DataFrame
        """
        if len(df):
            # if self.__dc_idx != 2:
            if self.__filters[0]:
                df = df[df.Subject.isin(self.__filters[0])]
            if self.__filters[1]:
                df = df[df.Session.isin(self.__filters[1])]
            if self.__filters[2]:
                if self.__dc_idx == 0:
                    df = df[df.DataType.isin(self.__filters[2])]
                else:
                    df = df[df.Pipeline.isin(self.__filters[2])]
            if self.__filters[3]:
                if self.__dc_idx == 1:
                    df = df[df.Step.isin(self.__filters[3])]
                elif self.__dc_idx == 2:
                    df = df[df.Report.isin(self.__filters[3])]
                else:
                    pass
            if self.__filters[4] is not None:
                file_tag = list(self.__filters[4])
                df = df[df.Filename.str.contains('|'.join(file_tag))]
            if self.__filters[5] is not None:
                ignore = list(self.__filters[5])
                df = df[~df.Filename.str.contains('|'.join(ignore))]
            if self.ext:
                df = df[df['Filename'].str.contains('|'.join([r"{ext}$".format(ext=ext) for ext in self.ext]))]
            return df
        else:
            return df

    def __summary(self):
        """Print summary of current project
        """
        summary = '** Project summary'
        summary = '{}\nProject: {}'.format(summary, os.path.basename(self.path))
        if self.__empty_project:
            summary = '{}\n[Empty project]'.format(summary)
        else:
            summary = '{}\nSelected DataClass: {}\n'.format(summary, self.dataclass)
            if self.pipelines:
                summary = '{}\nApplied Pipeline(s): {}'.format(summary, self.pipelines)
            if self.steps:
                summary = '{}\nApplied Step(s): {}'.format(summary, self.steps)
            if self.results:
                summary = '{}\nProcessed Result(s): {}'.format(summary, self.results)
            if self.subjects:
                summary = '{}\nSubject(s): {}'.format(summary, self.subjects)
            if self.sessions:
                summary = '{}\nSession(s): {}'.format(summary, self.sessions)
            if self.dtypes:
                summary = '{}\nDataType(s): {}'.format(summary, self.dtypes)
            if self.single_session:
                summary = '{}\nSingle session dataset'.format(summary)
            summary = '{}\n\nApplied filters'.format(summary)
            if self.__filters[0]:
                summary = '{}\nSet subject(s): {}'.format(summary, self.__filters[0])
            if self.__filters[1]:
                summary = '{}\nSet session(s): {}'.format(summary, self.__filters[1])
            if self.__dc_idx == 0:
                if self.__filters[2]:
                    summary = '{}\nSet datatype(s): {}'.format(summary, self.__filters[2])
            else:
                if self.__filters[2]:
                    summary = '{}\nSet Pipeline(s): {}'.format(summary, self.__filters[2])
                if self.__filters[3]:
                    if self.__dc_idx == 1:
                        summary = '{}\nSet Step(s): {}'.format(summary, self.__filters[3])
                    else:
                        summary = '{}\nSet Result(s): {}'.format(summary, self.__filters[3])
            if self.__ext_filter:
                summary = '{}\nSet file extension(s): {}'.format(summary, self.__ext_filter)
            if self.__filters[4]:
                summary = '{}\nSet file tag(s): {}'.format(summary, self.__filters[4])
            if self.__filters[5]:
                summary = '{}\nSet ignore(s): {}'.format(summary, self.__filters[5])
        print(summary)

    def __update(self):
        """Update attributes of Project object based on current set filter information
        """
        if len(self.df):
            try:
                if self.__dc_idx != 2:
                    self.__subjects = sorted(list(set(self.df.Subject.tolist())))
                    if self.single_session:
                        self.__sessions = None
                    else:
                        self.__sessions = sorted(list(set(self.df.Session.tolist())))
                    if self.__dc_idx == 0:
                        self.__dtypes = sorted(list(set(self.df.DataType.tolist())))
                        self.__pipelines = None
                        self.__steps = None
                        self.__results = None
                    elif self.__dc_idx == 1:
                        self.__dtypes = None
                        self.__pipelines = sorted(list(set(self.df.Pipeline.tolist())))
                        self.__steps = sorted(list(set(self.df.Step.tolist())))
                        self.__results = None
                else:
                    self.__subjects = sorted(list(set(self.df.Subject.tolist())))
                    if self.single_session:
                        self.__sessions = None
                    else:
                        self.__sessions = sorted(list(set(self.df.Session.tolist())))
                    self.__dtypes = None
                    self.__pipelines = sorted(list(set(self.df.Pipeline.tolist())))
                    self.__results = sorted(list(set(self.df.Report.tolist())))
                    self.__steps = None
            except:
                # self._logger.debug('__update::Error during update project attributes')
                methods.raiseerror(messages.Errors.UpdateAttributesFailed,
                                   "Error is occured during update project's attributes")
        else:
            self.__subjects = None
            self.__sessions = None
            self.__dtypes = None
            self.__pipelines = None
            self.__steps = None
            self.__results = None
            self.__empty_project = True

    def __call__(self, dc_id, *args, **kwargs):
        """Return DataFrame followed applying filters
        """
        prj = ccopy.copy(self)
        prj.dataclass = dc_id
        prj.set_filters(*args, **kwargs)
        prj.apply()
        return prj

    def __repr__(self):
        """Return absolute path for current filtered dataframe
        """
        if self.__empty_project:
            return str(self.summary)
        else:
            return str(self.df.Abspath)

    def __getitem__(self, index):
        """Return particular data based on input index
        """
        if self.__empty_project:
            return None
        else:
            return self.df.loc[index]

    def __iter__(self):
        """Iterator for dataframe
        """
        if self.__empty_project:
            raise messages.EmptyProject
        else:
            for row in self.df.iterrows():
                yield row

    def __len__(self):
        """Return number of data
        """
        if self.__empty_project:
            return 0
        else:
            return len(self.df)