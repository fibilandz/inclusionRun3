import os
import argparse
import luigi
from luigi.util import inherits

########################################################################
### ARGUMENT PARSING ###################################################
########################################################################
_tasks = ( 'submit', 'hadd', 'comp', 'drawsf')
_triggers = ('nonStandard', #>=9
             '9', '10', '11', '12',     #single trig
             '13', '14',
             )
_variables = ['met_et', 'HT20', 'mht_et', 'metnomu_et', 'mhtnomu_et', 'dau1_pt', 'dau2_pt']
_channels = ( 'all', 'etau', 'mutau', 'tautau', 'mumu' )
_data = dict( MET2018 = ['MET2018A',
                         'MET2018B',
                         'MET2018C',
                         'MET2018D',] )
_mc_processes = dict( Radions = ['Radion_m300',
                                 'Radion_m400',
                                 'Radion_m500',
                                 'Radion_m600',
                                 'Radion_m700',
                                 'Radion_m800',
                                 'Radion_m900',],
                  
                      SingleMuon = ['SingleMuon2018',
                                    'SingleMuon2018A',
                                    'SingleMuon2018B',
                                    'SingleMuon2018C',
                                    'SingleMuon2018D'],
                      
                      TT =         ['TT_fullyHad',
                                    'TT_fullyLep',
                                    'TT_semiLep',],
                      
                      DY =         ['DY',
                                    'DYall',
                                    'DY_lowMass',],
                     )
    
parser = argparse.ArgumentParser()
choices = [x for x in range(len(_tasks)+1)]
parser.add_argument(
    '--force',
    type=int,
    choices=choices,
    default=0,
    help="Force running a certain number of tasks, even if the corresponding targets exist.\n The value '" + str(choices) + "' runs the highest-level task and so on up to '" + str(choices[-1]) + "').\n It values follow the hierarchies defined in the cfg() class."
)
parser.add_argument(
    '--workers',
    type=int,
    default=1,
    help="Maximum number of worker which can be used to run the pipeline."
)
parser.add_argument(
    '--scheduler',
    type=str,
    choices=['local', 'central'],
    default='local',
    help='Select the scheduler for luigi.'
)
parser.add_argument(
    '--data',
    type=str,
    required=True,
    choices=_data.keys(),
    help='Select the data over which the workflow will be run.'
)
parser.add_argument(
    '--mc_process',
    type=str,
    required=True,
    choices=_mc_processes.keys(),
    help='Select the MC processes over which the workflow will be run.'
)
parser.add_argument(
    '--triggers',
    nargs='+', #1 or more arguments
    type=str,
    required=True,
    choices=_triggers,
    help='Select the processes over which the workflow will be run.'
)
parser.add_argument(
    '--channels',
    nargs='+', #1 or more arguments
    type=str,
    default=_channels,
    help='Select the channels over which the workflow will be run.'
)
parser.add_argument(
    '--variables',
    nargs='+', #1 or more arguments
    type=str,
    default=_variables,
    help='Select the variables over which the workflow will be run.'
)
parser.add_argument(
    '--tag',
    type=str,
    required=True,
    help='Specifies a tag to differentiate workflow runs.'
)
parser.add_argument(
    '--subtag',
    type=str,
    default='metnomu200cut',
    help='Specifies a cut.'
)
parser.add_argument(
    '--submit',
    action='store_true',
    help="Executes the submission to HTCondor."
)
parser.add_argument(
    '--debug_workflow',
    action='store_true',
    help="Explicitly print the functions being run for each task, for workflow debugging purposes."
)
FLAGS, _ = parser.parse_known_args()

########################################################################
### HELPER FUNCTIONS ###################################################
########################################################################
def set_task_name(n):
    "handles the setting of each task name"
    assert( n in _tasks )
    return n

########################################################################
### LUIGI CONFIGURATION ################################################
########################################################################
class cfg(luigi.Config):
    base_name = 'TriggerScaleFactors'
    data_base = os.path.join( '/data_CMS/', 'cms' )
    user = os.environ['USER']
    data_storage = os.path.join(data_base, user, base_name)
    data_target = 'MET2018_sum'

    ### Define luigi parameters ###
    # general
    tag = FLAGS.tag
    tag_folder = os.path.join(data_storage, tag)
    targets_folder = os.path.join(data_storage, tag, 'targets')
    targets_default_name = 'DefaultTarget.txt'
    targets_prefix = 'hist_eff_'

    data_input = '/data_CMS/cms/portales/HHresonant_SKIMS/SKIMS_Radion_2018_fixedMETtriggers_mht_16Jun2021/'

    ####
    #### submitTriggerEff
    ####
    _rawname = set_task_name('submit')
    submit_params = luigi.DictParameter(
        default={ 'taskname': _rawname,
                  'hierarchy': _tasks.index(_rawname)+1,
                  'indir': data_input,
                  'outdir': tag_folder,
                  'data': _data[FLAGS.data],
                  'mc_processes': _mc_processes[FLAGS.mc_process],
                  'triggers': FLAGS.triggers,
                  'channels': FLAGS.channels,
                  'variables': FLAGS.variables,
                  'subtag': FLAGS.subtag} )

    ####
    #### haddTriggerEff
    ####
    _rawname = set_task_name('hadd')
    hadd_params = luigi.DictParameter(
        default={ 'taskname': _rawname,
                  'hierarchy': _tasks.index(_rawname)+1,
                  'indir': tag_folder,
                  'subtag': FLAGS.subtag} )
    ####
    #### compareTriggers
    ####
    _rawname = set_task_name('comp')
    comp_params = luigi.DictParameter(
        default={ 'taskname': _rawname,
                  'hierarchy': _tasks.index(_rawname)+1,
                  'indir': tag_folder } )

    ####
    #### drawTriggerScaleFactors
    ####
    _rawname = set_task_name('drawsf')
    # clever way to flatten a nested list
    #_selected_mc_process = sum([ _mc_processes[proc] for proc in FLAGS.mc_process ], [])
    #_selected_data = sum([ _data[x] for x in FLAGS.data ], [])
    _selected_mc_process = _mc_processes[FLAGS.mc_process]
    _selected_data = _data[FLAGS.data]
    
    drawsf_params = luigi.DictParameter(
        default={ 'taskname': _rawname,
                  'hierarchy': _tasks.index(_rawname)+1,
                  'data_name': FLAGS.data,
                  'mc_name': FLAGS.mc_process,
                  'data': _selected_data,
                  'mc_processes': _selected_mc_process,
                  'indir': tag_folder,
                  'triggers': FLAGS.triggers,
                  'channels': FLAGS.channels,
                  'variables': FLAGS.variables,
                  'subtag': FLAGS.subtag,
                  'target_suffix': '_Sum' } )

"""
DATA:
@ bit position - path
0 - HLT_IsoMu24_v
1 - HLT_IsoMu27_v
2 - HLT_Ele32_WPTight_Gsf_v
3 - HLT_Ele35_WPTight_Gsf_v
4 - HLT_DoubleTightChargedIsoPFTau35_Trk1_TightID_eta2p1_Reg_v
5 - HLT_DoubleMediumChargedIsoPFTau40_Trk1_TightID_eta2p1_Reg_v
6 - HLT_DoubleTightChargedIsoPFTau40_Trk1_eta2p1_Reg_v
7 - HLT_DoubleMediumChargedIsoPFTauHPS35_Trk1_eta2p1_Reg_v
8 - HLT_IsoMu20_eta2p1_LooseChargedIsoPFTauHPS27_eta2p1_CrossL1_v
9 - HLT_IsoMu20_eta2p1_LooseChargedIsoPFTau27_eta2p1_CrossL1_v
10 - HLT_Ele24_eta2p1_WPTight_Gsf_LooseChargedIsoPFTauHPS30_eta2p1_CrossL1_v
11 - HLT_Ele24_eta2p1_WPTight_Gsf_LooseChargedIsoPFTau30_eta2p1_CrossL1_v
12 - HLT_VBF_DoubleLooseChargedIsoPFTau20_Trk1_eta2p1_v
13 - HLT_VBF_DoubleLooseChargedIsoPFTauHPS20_Trk1_eta2p1_v
14 - HLT_PFHT500_PFMET100_PFMHT100_IDTight_v
15 - HLT_PFMETNoMu120_PFMHTNoMu120_IDTight_v
16 - HLT_PFMETNoMu120_PFMHTNoMu120_IDTight_PFHT60_v
17 - HLT_MediumChargedIsoPFTau50_Trk30_eta2p1_1pr_MET100_v
18 - HLT_MediumChargedIsoPFTau50_Trk30_eta2p1_1pr_MET110_v
19 - HLT_MediumChargedIsoPFTau50_Trk30_eta2p1_1pr_MET130_v

MC:
@ bit position - path
0 - HLT_IsoMu24_v
1 - HLT_IsoMu27_v
2 - HLT_Ele32_WPTight_Gsf_v
3 - HLT_Ele35_WPTight_Gsf_v
4 - HLT_DoubleMediumChargedIsoPFTauHPS35_Trk1_eta2p1_Reg_v
5 - HLT_IsoMu20_eta2p1_LooseChargedIsoPFTauHPS27_eta2p1_CrossL1_v
6 - HLT_Ele24_eta2p1_WPTight_Gsf_LooseChargedIsoPFTauHPS30_eta2p1_CrossL1_v
7 - HLT_VBF_DoubleLooseChargedIsoPFTau20_Trk1_eta2p1_v
8 - HLT_VBF_DoubleLooseChargedIsoPFTauHPS20_Trk1_eta2p1_v
9 - HLT_PFHT500_PFMET100_PFMHT100_IDTight_v
10 - HLT_PFMETNoMu120_PFMHTNoMu120_IDTight_v
11 - HLT_PFMETNoMu120_PFMHTNoMu120_IDTight_PFHT60_v
12 - HLT_MediumChargedIsoPFTau50_Trk30_eta2p1_1pr_MET100_v
13 - HLT_MediumChargedIsoPFTau50_Trk30_eta2p1_1pr_MET110_v
14 - HLT_MediumChargedIsoPFTau50_Trk30_eta2p1_1pr_MET130_v
"""
