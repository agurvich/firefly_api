from __future__ import print_function

import numpy as np

import os 

from firefly_api.options import Options
from firefly_api.tween import TweenParams
from firefly_api.particlegroup import ParticleGroup
from firefly_api.errors import FireflyError,FireflyWarning,FireflyMessage,warnings
from firefly_api.json_utils import write_to_json,load_from_json

class Reader(object):
    """
    This class provides a framework to unify the Options and ParticleGroup classes
    to make sure that the user can easily produce Firefly compatible files. It also 
    provides some rudimentary data validation. You should use this Reader as a base
    for any custom readers you may build (and should use inheritance, as demonstrated
    below in FIREreader!
    """
    def __init__(self,
        JSONdir = None, ## abs path, must be a sub-directory of Firefly/data
        options = None,
        write_startup = 'append',# True -> write | False -> leave alone | "append" -> adds to existing file
        max_npart_per_file = 10**4,
        prefix = 'Data',
        clean_JSONdir = 0,
        tweenParams = None
        ):
        """
        `JSONdir=None` - This should be the name of the sub-directory that will
            contain your JSON files, if you are not running python from
            `/path/to/Firefly/data` it should be the absolute path.

        `options=None` - An `Options` instance, if you have created one you can
            pass it here. `None` will generate default options. `reader.options.listKeys()`
            will give you a list of the different available options you can set
            using `reader.options["option_name"] = option_value`. 

        `write_startup='append'` - This is a flag for whether `startup.json` file
            should be written. It has 3 values: `True` -> writes a new `startup.json`
            that will contain only this visualization, `'append'` -> which will
            add this visualization to an existing `startup.json` (or create a
            new one), this is the default option, or `False` -> which will not
            add an entry to `startup.json`.

        `max_npart_per_file=10000` - The maximum number of particles saved per file,
            don't use too large a number or you will have trouble loading
            the individual files in. 

        `prefix='Data'` - What you would like your `.json` files to be called when
            you run `reader.dumpToJSON`. The format is
            `(prefix)(particleGroupName)(fileNumber).json`.

        `clean_JSONdir=0` - Whether you would like to delete all `.json` files in
            the `JSONdir`. Usually not necessary (since `filenames.json` will be
            updated) but good to clean up after yourself.

        `tweenParams=None` - a tweenParams instance for automating a fly-through
            path by pressing `t` while within an open instance of Firefly.
        """

        ## where will firefly look for jsons
        ##  firefly_api lives in dataReader, so let's steal the 
        ##  path from there
        self.DATA_dir = os.path.join(
                os.path.dirname( ## /
                os.path.dirname( ## /dataReader
                os.path.dirname(  
                os.path.realpath(__file__)))),
                'static', ## /static
                'data') ## /static/data

        if JSONdir is None:
            FireflyMessage("JSONdir is None, defaulting to %s/%s"%(self.DATA_dir,prefix))
            JSONdir = os.path.join(
                self.DATA_dir,
                prefix)

        if options is not None:
            try:
                ## fun fact, assert isinstance(options,Options) won't work with jupyter notebooks
                ##  that use %load_ext autoreload
                assert options.__class__.__name__ == 'Options'
            except AssertionError:
                raise FireflyError("Make sure you use an Options instance to specify Firefly settings.")
        else:
            ## we'll use the default ones then
            options = Options()

        if tweenParams is not None:
            try:
                assert tweenParams.__class__.__name__ == 'TweenParams'
            except AssertionError:
                raise FireflyError("Make sure you use a TweenParams instance to specify fly-through paths.")

        self.tweenParams = tweenParams

        self.options = options
        ## absolute path of where to place all the data files in, must be a 
        ##  sub-directory of Firefly/data for Firefly to be able to find it.

        ## get rid of the trailing '/' if it's there
        if JSONdir[-1]==os.sep:
            JSONdir=JSONdir[:-1]

        self.JSONdir = JSONdir
        self.path_prefix,self.path = self.splitAndValidateDatadir()

        #write the startup file?
        self.write_startup = write_startup

        #set the maximum number of particles per data file
        self.max_npart_per_file = max_npart_per_file

        ## prefix for the datafiles e.g. FIREdata
        self.prefix = prefix

        #remove the data files in the dataDir directory before adding more?
        self.clean_JSONdir = clean_JSONdir 
    
        ## array of particle groups
        self.particleGroups = []

    def splitAndValidateDatadir(self):
        """
        Ensures that files will be output to a location that Firefly 
        can read, as well as splits the path so that filenames.json 
        references files correctly.
        """
        path_prefix,path = os.path.split(self.JSONdir)
        if path_prefix == '':
            path_prefix = os.getcwd()

        for validate in ['index.html','static','LICENSE','README.md']:
            try:
                assert validate in os.listdir(
                    os.path.join(
                        os.path.split(path_prefix)[0],
                        ".."))   
            except:
                warnings.warn(FireflyWarning(
                    "JSONdir: {} -- ".format(self.JSONdir)+
                    "is not a sub-directory of Firefly/static/data. "+
                    "\nThis may produce confusing or inoperable results. "+
                    "As such, we will create a symlink for you. You're "+
                    "welcome."))

        if not os.path.isdir(self.JSONdir):
            os.makedirs(self.JSONdir)

        return path_prefix,path

    def addParticleGroup(self,particleGroup):
        """
        Adds a particle group to the Reader instance and adds that particle group's
        options to the attached Options instance.
        Input:
            particleGroup - the particle group in question that you would like to add
        """

        ## data validation of new ParticleGroup happened in its initialization
        self.particleGroups = np.append(
            self.particleGroups,
            [particleGroup],axis=0)

        ## add this particle group to the reader's options file
        self.options.addToOptions(particleGroup)

        return self.particleGroups
    
    def dumpToJSON(
        self,
        loud=0):
        """
        Creates all the necessary JSON files to run Firefly, making sure they are
        properly linked and cross-reference correctly, using the attached Options
        instance's and particleGroups' outputToJSON() methods.
        Input:
            loud=0 - flag for whether warnings within each outputToJSON should be shown
        """

        filenamesDict = {}

        clean = self.clean_JSONdir
        ## write each particleGroup to JSON using their own method
        ##  save the filenames into a dictionary for filenames.json
        for particleGroup in self.particleGroups:
            FireflyMessage("outputting:",particleGroup)
            this_filenames_and_nparts = particleGroup.outputToJSON(
                self.path,
                self.path_prefix,
                self.prefix,
                loud=loud,
                nparts_per_file = self.max_npart_per_file,
                clean = clean)
            filenamesDict[particleGroup.UIname]=list(this_filenames_and_nparts)
            ## already cleaned once
            if clean:
                clean = False

        ## output the options file...
        self.options.outputToJSON(self.JSONdir,prefix=self.prefix,loud=loud)

        ## really... it has to be an array with a tuple with a 0 in the nparts spot? 
        filenamesDict['options'] = [(os.path.join(self.path,self.prefix+self.options.options_filename),0)]

        write_to_json(filenamesDict,os.path.join(self.JSONdir,'filenames.json'))

        ## add these files to the startup.json
        startup_path = os.path.join("data",self.path)
        if not os.path.dirname(self.JSONdir) == 'data':

            ## create a symlink so that data can 
            ##  be read from a "sub-directory"
            try:
                os.symlink(self.JSONdir,os.path.join(
                    self.DATA_dir,
                    self.path))
            except FileExistsError:
                FireflyMessage("Symlink already exists. Skipping.")

        startup_file = os.path.join(
            self.DATA_dir,
            'startup.json')

        if self.write_startup == 'append' and os.path.isfile(startup_file):
            startup_dict = load_from_json(startup_file)

            maxx = 0 
            need_to_add = True
            for key in startup_dict.keys():
                if int(key) > maxx: 
                    maxx = int(key)
                ## it's already in startup.json
                if startup_dict[key] == startup_path:
                    need_to_add = False
            
            if need_to_add:
                startup_dict[str(maxx+1)]=startup_path
                write_to_json(startup_dict,startup_file)

        elif self.write_startup:
            write_to_json({"0":startup_path},startup_file)

        ## write a tweenParams file if a TweenParams instance is attached to reader
        if hasattr(self,'tweenParams') and self.tweenParams is not None:
            self.tweenParams.outputToJSON(
                self.JSONdir,
                #prefix=self.prefix,
                loud=loud)
