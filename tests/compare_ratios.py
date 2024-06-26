# Coding: utf-8

_all_ = [ 'compare_ratios' ]

import os
import numpy as np
import glob
import argparse
import uproot as up

import matplotlib
import matplotlib.pyplot as plt
import mplhep as hep
plt.style.use(hep.style.ROOT)

mu, tau = '\u03BC','\u03C4'
dd = {"mumu": mu+mu, "mutau": mu+tau}

def build_path(base, channel, variable):
    path = os.path.join(base, channel, variable)
    return os.path.join(path, "eff_Data_Mu_MC_TT_DY_WJets_" + channel + "_" + variable + "_TRG_METNoMu120_CUTS_*.root")

def get_paths_and_labels(base, mode, channels, variable, year, var_units):
    if mode == "ranges":
        labels = ["full", r"$[180;350[\:\:{}$".format(var_units),
                  r"$[160;350[\:\:{}$".format(var_units), r"$[150;350[\:\:{}$".format(var_units),
                  r"$[140;350[\:\:{}$".format(var_units)]
        # transfer files with:
        # cp /data_CMS/cms/alves/TriggerScaleFactors/OpenCADI_18/Outputs/mutau/metnomu_et/eff_Data_Mu_MC_TT_DY_WJets_mutau_metnomu_et_TRG_METNoMu120_CUTS_mhtnomu_et_L_0p0_default.root full_mumu_fit.root
        paths = ["full_mumu_fit_"+year+".root", "180_mumu_fit_"+year+".root",
                 "160_mumu_fit_"+year+".root", "150_mumu_fit_"+year+".root",
                 "140_mumu_fit_"+year+".root"]
    elif mode == "channels":
        labels = (dd["mutau"], dd["mumu"])
        paths = ("150_mutau_fit_"+year+".root", "150_mumu_fit_"+year+".root")
    elif mode == "datasets":
        labels = (dd["mumu"]  + ", SingleMuon", dd["mumu"]  + ", DoubleMuon",
                  dd["mutau"] + ", SingleMuon", dd["mutau"] + ", DoubleMuon")
        paths = ("full_mumu_fit.root", "full_double_mumu_fit.root",
                 "full_mutau_fit.root", "full_double_mutau_fit.root")
    elif mode == "years":
        labels = ("UL16", "UL16APV", "UL17", "UL18")
        paths = ("150_mumu_fit_2016.root", "150_mumu_fit_2016APV.root",
                 "150_mumu_fit_2017.root", "150_mumu_fit_2018.root")

    ret = {}
    for p,l in zip(paths,labels):
        tmp = glob.glob(p)
        if len(tmp) != 1:
            print(tmp)
            raise RuntimeError('[ERROR] Path {} with pattern {} must have lenght 1.'.format(tmp, p))
        ret[tmp[0]] = l

    return ret

def sigmoid(x, params):
    """
    Sigmoid function to mimick the TF1 object.
    Uproot does not yet support TF1 reading.
    """
    return params[2] / (1 + np.exp(-params[0] * (x - params[1])))

def compare_ratios(paths, mode, variable, year, var_units):
    """
    Compare ratios in two modes.
    - Mode 'ranges': compare change in fit from changing the fit range
    - Mode 'channels': compare changes from fitting different channels
    """
    colors = ("blue", "green", "red", "purple", "darkorange")
    var_map = dict(metnomu_et=r"MET-no$\mu$")

    fit_ratios, idx_lims = [], []

    if mode != "years":
        fig, (ax1, ax2) = plt.subplots(2, sharex=True, gridspec_kw={'height_ratios': [3., 1.]})
    else:
        fig, ax1 = plt.subplots(1)
    plt.subplots_adjust(wspace=0, hspace=0)

    for ipath, (bpath, blabel) in enumerate(paths.items()):
        graph_sf = up.open(bpath + ":SF1D")
        
        fit_data = up.open(bpath + ":SigmoidFuncData")
        fit_mc = up.open(bpath + ":SigmoidFuncMC")

        fit_data_pars = fit_data.member('fFormula').member('fClingParameters')[:]
        fit_mc_pars   = fit_mc.member('fFormula').member('fClingParameters')[:]
        fit_xrange    = (fit_data.member('fXmin'), fit_data.member('fXmax'))
        assert fit_xrange == (fit_mc.member('fXmin'), fit_mc.member('fXmax'))

        fit_xvals = np.linspace(0, 900.1, num=10000)

        fit_data_yvals = sigmoid(fit_xvals, fit_data_pars)
        fit_mc_yvals   = sigmoid(fit_xvals, fit_mc_pars)

        # get fit validity range, otherwise the full function is plotted
        idx_lims.append( (np.argmax(fit_xvals > fit_xrange[0]),
                          np.argmax(fit_xvals > fit_xrange[1])) )
        idx_sel = slice(idx_lims[-1][0], idx_lims[-1][1], 1)

        # if mode == "ranges" we only want to plot SFs once (all are equal)
        if mode != "ranges" or ipath > 0:
            # plot efficiency values and error bars
            ax1.errorbar(graph_sf.values(axis="x"), graph_sf.values(axis="y"),
                         xerr=(graph_sf.errors(axis="x", which="low"), graph_sf.errors(axis="x", which="high")),
                         yerr=(graph_sf.errors(axis="y", which="low"), graph_sf.errors(axis="y", which="high")),
                         fmt='o', color="black" if mode == "ranges" else colors[ipath])
            
        fit_ratios.append(fit_data_yvals / fit_mc_yvals)

        # plot SF fit (Data/MC)
        ax1.plot(fit_xvals[idx_sel], fit_ratios[-1][idx_sel], '--', color=colors[ipath], label=blabel)
            
    ax1.set_ylabel("Data / MC", fontsize=20)
    ax1.legend(loc="lower right")

    line_opt = dict(color="grey", linestyle="--")
    met_cuts = [180., 160., 150., 140.]

    if mode == "ranges":
        ax1.set_xlim(130, 360)
        ax1.set_ylim(-0.05, 1.19)
        yticks = (-0.16, -0.1, -0.05, 0., 0.05, 0.06)
        ax2.set_yticks(yticks)
        for yval in yticks:
            ax2.axhline(y=yval, **line_opt)
        ax2.set_ylim(yticks[0]+1E-5, yticks[-1]-1E-5)
        ax1.axhline(y=1., **line_opt)
        for cut in met_cuts:
            ax1.axvline(x=cut, **line_opt)
            ax2.axvline(x=cut, **line_opt)

    elif mode == "channels":
        ax1.set_ylim(-0.05, 1.12)
        ax1.axvline(x=150., **line_opt)
        ax2.axvline(x=150., **line_opt)
        yticks = (-0.15, -0.1, 0., 0.1, 0.15)
        ax2.set_yticks(yticks)
        ax1.axhline(y=1., **line_opt)
        for yval in yticks:
            ax2.axhline(y=yval, **line_opt)
        ax2.set_ylim(yticks[0]+1E-5, yticks[-1]-1E-5)

    elif mode == "datasets":
        ax1.set_ylim(-0.05, 1.08)
        ax1.axvline(x=150., **line_opt)
        ax2.axvline(x=150., **line_opt)
        yticks = np.arange(-.7, .7, .3)
        ax2.set_yticks(yticks)
        ax1.axhline(y=1., **line_opt)
        for yval in yticks:
            ax2.axhline(y=yval, **line_opt)
        ax2.set_ylim(yticks[0]+1E-5, yticks[-1]-1E-5)

    elif mode == "years":
        ax1.set_ylim(-0.05, 1.08)
        ax1.axvline(x=150., **line_opt)
        ax1.axhline(y=1., **line_opt)

    # comparison of ratios using the first partial fit as reference
    # the x range is the minimum interval common to both ratios
    if mode == "ranges":
        for ipath, (bpath,_) in enumerate(paths.items()):
            # if ipath == 0:
            #     continue
            tmp_sel = slice(max(idx_lims[1][0], idx_lims[ipath][0]),
                            min(idx_lims[1][1], idx_lims[ipath][1]), 1)
            ax2.plot(fit_xvals[tmp_sel], (fit_ratios[3][tmp_sel]/fit_ratios[ipath][tmp_sel])-1., '--', color=colors[ipath])

    elif mode == "channels":
        ax2.plot(fit_xvals, (fit_ratios[1]/fit_ratios[0])-1., '--', color="black")
    elif mode == "datasets":
        ax2.plot(fit_xvals, (fit_ratios[1]/fit_ratios[0])-1., '--', color="blue",
                 label=dd["mumu"] + ": Double/Single")
        ax2.plot(fit_xvals, (fit_ratios[3]/fit_ratios[2])-1., '--', color="orange",
                 label=dd["mutau"] + ": Double/Single")

    if mode == "ranges":
        ax2.set_ylabel(r"$(SF_{{150\:{u}}}/SF_{{X\:{u}}}) - 1$".format(u=var_units), fontsize=20)
    elif mode == "channels":
        ax2.set_ylabel(r"Fit Ratio", fontsize=20)
    elif mode == "datasets":
        ax2.set_ylabel(r"Fit Ratio", fontsize=20)

    if mode != "years":
        ax2.set_xlabel(var_map[variable] + " [" + var_units + "]", fontsize=21)
    else:
        ax1.set_xlabel(var_map[variable] + " [" + var_units + "]", fontsize=21)
        
    if mode == "datasets":
        ax2.legend(loc="lower right", fontsize=15)
        
    hep_opt = dict(ax=ax1)
    lumi = {"2016APV": "19.5", "2016": "16.8", "2017": "41.5", "2018": "59.7"}[year]
    hep.cms.text(' Preliminary', fontsize=22, **hep_opt)
    if mode == "ranges":
        hep.cms.lumitext(dd["mumu"] + " (baseline, {}) | ".format(year) + r"{} $fb^{{-1}}$ (13 TeV)".format(lumi),
                         fontsize=19, **hep_opt)
    elif mode == "years":
        hep.cms.lumitext(r"13 TeV", fontsize=19, **hep_opt)
    elif mode == "channels":
        hep.cms.lumitext(r"{} $fb^{{-1}}$ (13 TeV)".format(lumi), fontsize=19, **hep_opt)
    else:
        hep.cms.lumitext(r"59.7 $fb^{-1}$ (13 TeV)", fontsize=19, **hep_opt)

    baseout = "/eos/home-b/bfontana/www/TriggerScaleFactors/CompareRatios/"
    if mode == "years":
        output = os.path.join(baseout, os.path.basename(__file__[:-3] + '_' + mode))
    else:
        output = os.path.join(baseout, os.path.basename(__file__[:-3] + '_' + mode + '_' + year))
        
    for ext in ('.png', '.pdf'):
        fig.savefig(output + ext)
        print('Plot saved under {}'.format(output + ext))

    
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Compare efficiency ratios obtained with two different methods.')
    parser.add_argument('--tag', required=False, default="",
                        help='Tag used to produce the graphs. Same used by the inclusion/run.py command.')
    parser.add_argument('--mode', default="channel", choices=("ranges", "channels", "datasets", "years"),
                        help='Which comparison to run.')
    parser.add_argument('--year', default="2018", choices=("2016APV", "2016", "2017", "2018"),
                        help='Which data period to consider.')
    
    FLAGS = parser.parse_args()
    if FLAGS.mode == "channels":
        assert FLAGS.tag != ""
    
    base = os.path.join("/data_CMS/cms/alves/TriggerScaleFactors/", FLAGS.tag, "Outputs")
    paths = get_paths_and_labels(base, FLAGS.mode, channels=("mutau", "mumu"),
                                 variable="metnomu_et", year=FLAGS.year, var_units="GeV")
    compare_ratios(paths, mode=FLAGS.mode, variable="metnomu_et", year=FLAGS.year, var_units="GeV")
