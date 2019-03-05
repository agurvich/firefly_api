from __future__ import print_function
import numpy as np
import pandas as pd
import copy
import h5py,os, shutil

import warnings

from firefly.options import Options
class ParticleGroup(object):
    """
    This is a class for organizing data that you want to interface with a 
    Reader instance. This class provides rudimentary data validation and 
    options defaults specific to this data class. If you do not intend
    to attach it to a Reader instance using that reader's addParticleGroup
    method please be careful!!
    """

    def __repr__(self):
        """
        Implementation of builtin function __repr__
        """
        mystr = "Particle Group of %s\n"%(self.UIname)
        mystr += "Contains %d (%d after dec) particles and %d arrays\n"%(
            self.nparts,self.nparts/self.decimation_factor,len(self.tracked_names))
        return mystr

    def __getitem__(self,key):
        """
        Implementation of builtin function __getitem__
        """
        if key == 'Coordinates':
            return self.coordinates

        elif key in self.tracked_names:
            return self.tracked_arrays[self.tracked_names.index(key)]
        else:
            raise KeyError("%s is not a tracked array"%key)
    
    def __setitem__(self,key,value):
        """
        Implementation of builtin function __setitem__
        """
        if key == 'Coordinates':
            self.coordinates=value
        elif key in self.tracked_names:
            self.tracked_arrays[self.tracked_names.index(key)]=value
        else:
            raise KeyError("%s is not a tracked array"%key)
        
    def __init__(
        self,
        UIname,
        coordinates,
        tracked_arrays = [],
        tracked_names = [],
        tracked_filter_flags = [],
        tracked_colormap_flags = [],
        decimation_factor = 1,
        filenames_and_nparts = None,
        **option_kwargs):
        """
        `UIname` - Name of the particle group that shows up in the UI, 4-5 characters is best

        `coordinates` - The coordinates of the points in 3d space, should have a shape of `(nparts,3)`.

        `tracked_arrays=[]` - The arrays to associate with each coordinate in space, each array
            should be one-dimensional and have `nparts` entries.

        `tracked_names=[]` - Should be the same length as `tracked_arrays`, and gives a
            name to each of the arrays when they show up in the UI dropdowns.

        `tracked_filter_flags=[]` - Should be the same length as `tracked_arrays`,
            and gives a flag for whether that array should be available as an interactive filter within Firefly.
        `tracked_colormap_flags=[]` - Should be the same length as `tracked_arrays`,
            and gives a flag for whether that array should be available to color points within Firefly.

        `decimation_factor=1` - An integer factor to sub-sample the provided dataset at
            (in addition to any manual subsampling you might do). This will choose
            `nparts/decimation_factor` many points at random from the dataset to display in Firefly. 

        `filenames_and_nparts=None` - Allows you to manually control how the particles
            are distributed among the JSON files, **highly recommended that
            you leave this to** `None`, but if for whatever reason you need fine-tuning
            you should pass a list of tuples in the form 
            `[("json_name0.json",nparts_this_file0),("json_name1.json",nparts_this_file1) ... ]`
            where where the sum of `nparts_this_file%d` is exactly `nparts`. These files
            will automatically be added to `filenames.json` if you use `reader.dumpToJSON`.

        `**option_kwargs` - allows you to set default options like the color, particle sizes,
            etc... for this particle group at the creation of the instance. You can see available
            options by looking at `list(particleGroup.options_default.keys())`.
        """
        ## assert statements and user-friendly error messages
        try:
            assert len(tracked_names) == len(tracked_arrays)
        except:
            raise ValueError("Make sure each tracked_array has a tracked_name")
    
        try: 
            assert len(tracked_names) == len(tracked_filter_flags)
        except:
            print(tracked_names,tracked_filter_flags)
            warnings.warn("Make sure each tracked_array has a tracked_filter_flag, assuming True.")
            new_tracked_filter_flags = np.append(
                tracked_filter_flags,
                [True]*(len(tracked_names)-len(tracked_filter_flags)),axis=0
            )
            print(tracked_filter_flags,"becomes ->",new_tracked_filter_flags)
            tracked_filter_flags = new_tracked_filter_flags

        try: 
            assert len(tracked_names) == len(tracked_colormap_flags)
        except:
            print(tracked_names,tracked_colormap_flags)
            warnings.warn("Make sure each tracked_array has a tracked_colormap_flag, assuming True.")
            new_tracked_colormap_flags = np.append(
                tracked_colormap_flags,
                [True]*(len(tracked_names)-len(tracked_colormap_flags)),axis=0
            )
            print(tracked_colormap_flags,"becomes ->",new_tracked_colormap_flags)
            tracked_colormap_flags = new_tracked_colormap_flags

        
        if filenames_and_nparts is not None:
            try:
                assert type(filenames_and_nparts[0]) == tuple
                assert type(filenames_and_nparts[0][0]) == str
                assert type(filenames_and_nparts[0][1]) == int
            except AssertionError:
                ValueError("filenames_and_nparts should be a list of tuples of strings and ints")
        
        self.decimation_factor = decimation_factor
        ## what do we want this to be called in the UI? 
        self.UIname = UIname

        ## the most important thing, where do you want these particles
        ##  to live?
        self.coordinates = coordinates

        ## initialize this badboy
        self.nparts = len(coordinates)

        ## these are the values we're associating with each particle
        ##  make sure each one has a name
        for name,array in zip(tracked_names,tracked_arrays):
            try:
                assert len(array) == self.nparts
            except:
                raise ValueError("You passed me %s that is not the right shape!"%name)

        self.tracked_names = tracked_names
        self.tracked_arrays = tracked_arrays
        self.tracked_filter_flags = tracked_filter_flags
        self.tracked_colormap_flags = tracked_colormap_flags

        self.filenames_and_nparts = filenames_and_nparts

        ## TODO how do these interface with javascript code?
        self.radiusFunction = None
        self.weightFunction = None

        ## setup the options for this particleGroup 
        self.options_default = {
            'UIparticle':True,
            'UIdropdown':True,
            'UIcolorPicker':True,
            'color': np.append(np.random.random(3),[1]),
            'sizeMult':1.,
            'showParts':True,
            'filterVals':dict(),
            'filterLims':dict(),
            'colormapVals':dict(),
            'colormapLims':dict(),
            'showVel':False,
            'plotNmax':None,
            'velType':None
        }
        
        ## setup default values for the initial filter limits (vals/lims represent the interactive
        ##  "displayed" particles and the available boundaries for the limits)
        for tracked_name,tracked_filter_flag in zip(self.tracked_names,self.tracked_filter_flags):
            if tracked_filter_flag:
                self.options_default['filterVals'][tracked_name] = None
                self.options_default['filterLims'][tracked_name] = None

        ## setup default values for the initial color limits (vals/lims represent the interactive
        ##  "displayed" particles and the available boundaries for the limits)
        for tracked_name,tracked_colormap_flag in zip(self.tracked_names,self.tracked_colormap_flags):
            if tracked_filter_flag:
                self.options_default['colormapVals'][tracked_name] = None
                self.options_default['colormapLims'][tracked_name] = None
        
        ## now let the user overwrite the defaults if they'd like (e.g. the color, likely
        ##  the most popular thing users will like to do
        for option_kwarg in option_kwargs:
            if option_kwarg in self.options_default.keys():
                if option_kwarg == 'color':
                    try:
                        assert len(option_kwargs[option_kwarg]) == 4
                    except AssertionError:
                        raise ValueError("Make sure you pass the color as an RGBA array")
                        
                self.options_default[option_kwarg] = option_kwargs[option_kwarg]
            else:
                raise KeyError("Invalid option kwarg")

        ## functions that should happen after initialization: 
        ##  get that decimation index array so when we write out we 
        ##  have it ready (but still be able to add stuff whenever)
        self.getDecimationIndexArray()
        
    def trackArray(self,name,arr,filter_flag=1,colormap_flag=1):
        """
        Adds a new "tracked" array to the particle group
        Input:
            name - name of the tracked array in the UI
            arr - the array itself
            filter_flag=1 - whether this array should be filterable in the app
        """
        ## check that it's the correct length
        assert self.nparts == len(arr)

        ## go ahead and put it in the tracked arrays
        self.tracked_names += [name]
        self.tracked_arrays += [arr]
        self.tracked_filter_flags += [filter_flag]
        self.tracked_colormap_flags += [colormap_flag]

        ## and add this to the filter limits arrays, see __init__ above
        if filter_flag: 
            self.options_default['filterVals'][name] = None
            self.options_default['filterLims'][name] = None

        ## and add this to the color limits arrays, see __init__ above
        if colormap_flag: 
            self.options_default['colormapVals'][name] = None
            self.options_default['colormapLims'][name] = None

        if self.linked_options is not None:
            self.linked_options['filterVals'][self.UIname][name] = None
            self.linked_options['filterLims'][self.UIname][name] = None

            self.linked_options['colormapVals'][self.UIname][name] = None
            self.linked_options['colormapLims'][self.UIname][name] = None

    def getDecimationIndexArray(self):
        """
        Creates a numpy index array to handle decimation (sub-sampling) of your
        data. Chooses nparts/decimation_factor many particles randomly without
        replacement.
        """
        if self.decimation_factor > 1:
            ## use an array of indices
            self.dec_inds = np.random.choice(
                np.arange(self.nparts),int(self.nparts/self.decimation_factor),
                replace=False)
        else:
            ## use a boolean mask instead
            self.dec_inds = np.ones(self.nparts,dtype=bool)

    def outputToJSON(
        self,
        path, ## sub-directory name
        path_prefix, ## absolute path to Firefly/data
        prefix, ## prefix of JSON filename
        loud=1,
        nparts_per_file = 10**4,
        clean=0):
        """
        Outputs this ParticleGroup instance's data to JSON format, best used when coupled with a Reader
        instance's dumpToJSON method. 
        Input:
            path - the name of the sub-directory of Firefly/data you want to put these files into
            path_prefix - the the path to Firefly/data
            prefix - the string you want to prepend to the data JSONs
            loud=1 - flag to print warnings that you should hear if you're not using a
                reader that does these things for you
            nparts_per_file=10**4 - maximum number of particles per JSON file
            clean=0 - flag for whether the JSON directory should be purged before writing your files.
         """
        full_path = os.path.join( path_prefix, path )
        if not os.path.isdir(full_path):
            os.makedirs(full_path)
        if loud:
            warnings.warn("You will need to add the sub-filenames to"+
                " filenames.json if this was not called by a Reader instance.")
            print("Writing:",self,"JSON to %s"%full_path)
        if clean:
            warnings.warn("Removing data files from %s"%full_path)
            for fname in os.listdir(full_path):
                if "json" in fname:
                    os.remove(os.path.join(full_path,fname))

        if self.filenames_and_nparts is None:
            if self.dec_inds.dtype == bool:
                nparts = np.sum(self.dec_inds)
            else:
                nparts = self.dec_inds.shape[0]
            nfiles = int(nparts/nparts_per_file + ((nparts%nparts_per_file)!=0))
            filenames = [os.path.join(path,"%s%s%03d.json"%(prefix,self.UIname,i_file)) for i_file in range(nfiles)]
            nparts = [min(nparts_per_file,nparts-(i_file)*(nparts_per_file)) for i_file in range(nfiles)]
            self.filenames_and_nparts = list(zip(filenames,nparts))
        
        cur_index = 0
        for i_file,(fname,nparts_this_file) in enumerate(self.filenames_and_nparts):
            ## which particles to save?
            if self.decimation_factor > 1:
                these_dec_inds = self.dec_inds[cur_index:cur_index+nparts_this_file]
            else:
                these_dec_inds = np.arange(cur_index,cur_index+nparts_this_file)

            outDict = dict()
            outDict['Coordinates'] = self.coordinates[these_dec_inds]

            for tracked_name,tracked_arr in zip(self.tracked_names,self.tracked_arrays):
                outDict[tracked_name]=tracked_arr[these_dec_inds]

            cur_index+=nparts_this_file
            if i_file == 0:
                print(self.tracked_names,
                    'filter:',self.tracked_filter_flags,
                    'colormap:',self.tracked_colormap_flags)
                outDict['filterKeys'] = np.array(self.tracked_names)[np.array(
                    self.tracked_filter_flags,dtype=bool)]
                outDict['colormapKeys'] = np.array(self.tracked_names)[np.array(
                    self.tracked_colormap_flags,dtype=bool)]

                ## TODO this needs to be changed, this is a flag for having the
                ##  opacity vary across a particle as the impact parameter projection
                ##  of cubic spline kernel
                outDict['doSPHrad'] = [0]

            pd.Series(outDict).to_json(os.path.join(path_prefix,fname), orient='index')

        return self.filenames_and_nparts

    def outputToHDF5(self):
        """
        Hook for a future implementation of Firefly that can use HDF5 formats.
        """
        raise Exception("Unimplemented!")

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
        """
        if options is not None:
            try:
                ## fun fact, assert isinstance(options,Options) won't work with jupyter notebooks
                ##  that use %load_ext autoreload
                assert options.__class__.__name__ == 'Options'
            except AssertionError:
                raise ValueError("Make sure you use an Options instance to specify Firefly settings.")
        else:
            ## we'll use the default ones then
            options = Options()

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
        for validate in ['index.html','data','src','LICENSE','README.md']:
            try:
                assert validate in os.listdir(os.path.split(path_prefix)[0])   
            except:
                IOError("JSONdir is not a sub-directory of a version of Firefly/data")
        return path_prefix,path

    def addParticleGroup(self,particleGroup):
        """
        Adds a particle group to the Reader instance and adds that particle group's
        options to the attached Options instance.
        Input:
            particleGroup - the particle group in question that you would like to add
        """
        ## data validation of new ParticleGroup happened in its initialization
        self.particleGroups += [particleGroup]

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
            print("outputting",particleGroup)
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
        pd.Series(filenamesDict).to_json(os.path.join(self.JSONdir,'filenames.json'), orient='index')  

        ## add these files to the startup.json
        startup_path = os.path.join("data",self.path)
        startup_file = os.path.join(self.path_prefix,'startup.json')
        if self.write_startup == 'append' and os.path.isfile(startup_file):
            with open(startup_file,'r+') as handle:
                startup_dict=pd.io.json.loads(''.join(handle.readlines()))

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
                pd.Series(startup_dict).to_json(startup_file,orient='index')

        elif self.write_startup:
            pd.Series({"0":startup_path}).to_json(startup_file, orient='index') 
