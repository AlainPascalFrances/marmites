# -*- coding: utf-8 -*-
"""
MARMITES is a distributed depth-wise lumped-parameter model for
spatio-temporal assessment of water fluxes in the unsaturated zone.
MARMITES is a french word to
design a big cooking pot used by sorcerers for all kinds of experiments!
The main objective of MARMITES development is to partition the rainfall
in the several fluxes from the unsaturated and saturated zone (source
reservoir). It applies the concepts enunciated by Lubcynski (2010):                        ## TO BE UPDATED## 20100823
ET = Es + I + ETu + ETg
ETu = Eu + Tu
ETg = Eg + Tg
MARMITES is a modular algorithm that computes on a daily temporal
basis: interception, surface storage and runoff, evaporation from the
unsaturated and saturated zone (from MODFLOW), soil moisture storage,
aquifer recharge.
Input driving forces are rainfall and potential evapotranspiration daily
time series.
Calibration is made against soil moisture (DPLWATFLUX) and hydraulic
heads (MODFLOW).
It is link to MODFLOW2000 (mf2k) and the calibration is done
through PEST (Doherty 2010).
MARMITES imports and exports mf2k packages for spatial and temporal
discretization, intial heads, recharge, etc.
Thanks to Toews 2007 and flopy.                                         ## TO BE UPDATED## 20100823
For more documentation, see Frances et al 2010.                         ## TO BE UPDATED## 20100823
References:
Lub 2010
Frances et al 2010                                                      ## TO BE UPDATED## 20101015
"""

__author__ = "Alain Francés <frances08512@itc.nl>"
__version__ = "1.0"
__date__ = "November 2010"

import os
import numpy as np

class UNSAT:

    """
    unsat class: compute the water balance in soil (depth-wise, each reservoir
    correspond to a soil horizon (A, B, C and rock)
    ## TO BE UPDATED""
    _______________________________________________________________________________

    INPUTS
            PARAMETERS
                MAXIL       Interception looses
                Sm          Max. Soil moiture storage
                Sfc         Soil moiture storage at field capacity
                Sr          Residual Soil moiture storage
                Su_ini          Inicial soil moisture
                Ks          Saturated hydraulic condutivity
                Ss_max       Max. ponding capacity
            STATE VARIABLES
                RF           Daily rainfall
                PET         Daily evapotranspiration
    OUTPUTS
            RFe              Daily Excess rainfall
            ETu             Daily evapotranspiration
            Su               Daily soil moisture
            Rp              Daily percolation
            Ss            Daily ponding
            Ro              Daily runoff

    Provide daily values for the LINRES module
    ______________________________________________________________________________

    """

    def __init__(self, hnoflo):
        self.hnoflo = hnoflo

##        @ARTICLE{Shah2007,
##          author = {Shah, Nirjhar and Nachabe, Mahmood and Ross, Mark},
##          title = {Extinction Depth and Evapotranspiration from Ground Water under Selected
##        	Land Covers},
##          journal = {Ground Water},
##          year = {2007},
##          volume = {45},
##          pages = {329-338},
##          number = {3},
##        }
        # table 5, values for bare soil
        # dll [cm], y0 [], b [cm^-1], ext_d [cm]
        self.paramEg = {'sand'           : {'dll':16.0,'y0':0.000,'b':0.171, 'ext_d':50.0},
                       'loamy sand'      : {'dll':21.0,'y0':0.002,'b':0.130, 'ext_d':70.0},
                       'sandy loam'      : {'dll':30.0,'y0':0.004,'b':0.065, 'ext_d':130.0},
                       'sandy clay loam' : {'dll':30.0,'y0':0.006,'b':0.046, 'ext_d':200.0},
                       'sandy clay'      : {'dll':20.0,'y0':0.005,'b':0.042, 'ext_d':210.0},
                       'loam'            : {'dll':33.0,'y0':0.004,'b':0.028, 'ext_d':260.0},
                       'silty clay'      : {'dll':37.0,'y0':0.007,'b':0.046, 'ext_d':330.0},
                       'clay loam'       : {'dll':33.0,'y0':0.008,'b':0.027, 'ext_d':400.0},
                       'silt loam'       : {'dll':38.0,'y0':0.006,'b':0.019, 'ext_d':420.0},
                       'silt'            : {'dll':31.0,'y0':0.007,'b':0.021, 'ext_d':430.0},
                       'silty clay loam' : {'dll':40.0,'y0':0.007,'b':0.021, 'ext_d':450.0},
                       'clay'            : {'dll':45.0,'y0':0.006,'b':0.019, 'ext_d':620.0}
}

#####################

    def flux(self, RFe, PET, PE, Su, Rp, Zr_elev, VEGarea, HEADS, HEADS_ini, Tltop, Tlbot, Tl, Tll_ini, nsl, Sm, Sfc, Sr, Ks, Ss_max, Ss_ratio, t, Su_ini, Rp_ini, DRN, DRN_ini, Ss_ini, E0, dtwt, st, i, j, n, kTu_min, kTu_n, dt, dti):

        global Rexf_tmp, R_tmp, Su_tmp, Tu_tmp, Eu_tmp, Rp_tmp, Ro_tmp, Es_tmp, Tu_tmpZr, Ss_tmp

        def surfwater(s_tmp,Sm,Ss_max, E0, i, j, n, dt):
            '''
            Ponding and surface runoff function
            '''
            if s_tmp > Sm:
                Ss_tmp = s_tmp-Sm
                if Ss_tmp > Ss_max or np.abs(Ss_tmp - Ss_max) < 1.0E-7:
                    Ro_tmp = (Ss_tmp-Ss_max)/dt
                    Ss_tmp = Ss_max
                else:
                    Ro_tmp = 0.0
                if Ss_tmp > E0 or np.abs(Ss_tmp - E0) < 1.0E-7:
                    Es_tmp = E0
                    Ss_tmp = Ss_tmp - E0*dt
                else:
                    Es_tmp = Ss_tmp/dt
                    Ss_tmp = 0.0
            else:
                Ss_tmp = 0.0
                Ro_tmp = 0.0
                Es_tmp = 0.0
            return Ss_tmp, Ro_tmp, Es_tmp

        ##################

        def perc(s_tmp, Sm, Sfc, Ks, s_lp1, Sm_sp1, i, j, n, dt):
            '''
            Percolation function
            '''
            global rp_tmp
            if Sfc > s_tmp or np.abs(s_tmp-Sfc) < 1.0E-7:
                rp_tmp = 0.0
            elif s_tmp > Sfc and ( Sm > Sfc or np.abs(s_tmp-Sm) < 1.0E-7):
                Sg = (s_tmp-Sfc)/(Sm-Sfc) # gravitational water
                if (Ks*Sg*dt) > (s_tmp-Sfc):
                    rp_tmp = (s_tmp-Sfc)/dt
                else:
                    rp_tmp = Ks*Sg
            elif s_tmp > Sm:
                if (Ks*dt) > (Sm-Sfc):
                    rp_tmp = (Sm-Sfc)/dt
                else:
                    rp_tmp = Ks
            # verify the vol. available in deeper soil layer
            if (rp_tmp*dt) > (Sm_sp1 - s_lp1):
                rp_tmp = (Sm_sp1 - s_lp1)/dt
            return rp_tmp

        ##################

        def evp(s_tmp,Sfc,Sr, pet, i, j, n, dt):
            '''
            Actual evapotranspiration function
            '''
            global evp_tmp
            if (s_tmp - Sr) <= 1E-9:
                evp_tmp = 0.0
            elif ((s_tmp - Sr) > 1E-9) and ((s_tmp < Sfc) or np.abs(s_tmp -Sfc) < 1.0E-7):
                Se = (s_tmp - Sr)/(Sfc - Sr)
                if (pet*Se*dt - (s_tmp - Sr)) > 1.0E-7:
                    evp_tmp = (s_tmp - Sr)/dt
                else:
                    evp_tmp = pet*Se
            elif (s_tmp - Sfc) > 1.0E-7:
                if (pet*dt-(Sfc - Sr)) > 1.0E-7:
                    evp_tmp = (Sfc - Sr)/dt
                else:
                    evp_tmp = pet
            return evp_tmp

##            if s_tmp <= 0.0 :
##                evp_tmp = 0.0
##            elif (s_tmp > 0.0) and ((s_tmp < Sfc) or np.abs(s_tmp -Sfc) < 1.0E-7):
##                Se = s_tmp/Sfc
##                if (pet*Se*dt) > s_tmp:
##                    evp_tmp = s_tmp/dt
##                else:
##                    evp_tmp = pet*Se
##            elif s_tmp > Sfc :
##                if (pet*dt) > Sfc:
##                    evp_tmp = Sfc/dt
##                else:
##                    evp_tmp = pet
##            return evp_tmp


        ##################
        if DRN < 0.0:
            print 'WARNING!\nDRN < 0.0, value %.6f corrected to 0.0.' % DRN
            DRN = 0.0
        MB_err = 0.0
        SAT = np.zeros([nsl], dtype = bool)
        if DRN == 0.0:
            # Su_tmp from previous time step
            # if first time step, use Su_ini
            Su_tmp = np.zeros([nsl])
            Rexf_tmp = np.zeros([nsl])
            for l in range(nsl-1):
                Su_tmp[l] = Su_ini[l]
            if DRN_ini == 0.0:
                Su_tmp[nsl-1] = Su_ini[nsl-1]
            elif DRN_ini > 0.0:
                MB_err += Sfc[nsl-1]*Tl[nsl-1]
                Su_tmp[nsl-1] = Sr[nsl-1]*Tl[nsl-1]
            # correction of the vadose zone due to thickness change
            if HEADS_ini > HEADS:
                MB_err += (HEADS_ini - HEADS)*Sfc[nsl-1]
                Su_tmp[nsl-1] += (HEADS_ini - HEADS)*Sfc[nsl-1]

            # INFILTRATION
            # first soil layer
            Su_tmp[0] += RFe*dt + Ss_ini
            # other soil layer, percolation from previous time step
            for l in range(1,nsl):
                if t == 0:
                    Su_tmp[l] += Rp_ini[l-1]*dti
                else:
                    Su_tmp[l] += Rp[t-1,l-1]*dti

            # EXFILTRATION
            llst = range(nsl)
            llst.reverse()
            for l in llst[:-1]:
                if Su_tmp[l] > Sm[l]*Tl[l]:
                    Rexf_tmp[l] += Su_tmp[l] - Sm[l]*Tl[l]
                    Su_tmp[l-1] += Rexf_tmp[l]
                    Su_tmp[l] = Sm[l]*Tl[l]

            # Ss and Ro
            surfwater_tmp = surfwater(Su_tmp[0],Sm[0]*Tl[0],Ss_max, E0*Ss_ratio, i, j, n, dt)
            Ss_tmp = surfwater_tmp[0]
            Ro_tmp = surfwater_tmp[1]
            Es_tmp = surfwater_tmp[2]
            Rexf_tmp[0] += sum(surfwater_tmp)
            Su_tmp[0] -= (Ss_tmp + dt*(Ro_tmp + Es_tmp))

            Rp_tmp = np.zeros([nsl])
            R_tmp = 0.0
            Tu_tmpZr = np.zeros([nsl,len(Zr_elev)])
            Tu_tmp = np.zeros([nsl])
            Eu_tmp = np.zeros([nsl])
            Su_pc_tmp = np.zeros([nsl])
            # soil layers and vadose zone layer
            for l in range(nsl):
                # Rp
                if l < (nsl-1):
                    Rp_tmp[l] = perc(Su_tmp[l],Sm[l]*Tl[l],Sfc[l]*Tl[l],Ks[l], Su_tmp[l+1], Sm[l+1]*Tl[l+1], i, j, n, dt)
                    Su_tmp[l] -= Rp_tmp[l]*dt
                else:
                    Rp_tmp[l] = perc(Su_tmp[l],Sm[l]*Tl[l],Sfc[l]*Tl[l], Ks[l],0.0,1.0E6, i, j, n, dt)
                    Su_tmp[l] -= Rp_tmp[l]*dt
                    R_tmp += Rp_tmp[l]
            for l in range(nsl):
                # Eu
                if Ss_tmp == 0.0:
                    if PE > 0.0:
                        Eu_tmp[l] = evp(Su_tmp[l],Sfc[l]*Tl[l], Sr[l]*Tl[l], PE, i, j, n, dt)
                        Su_tmp[l] -= Eu_tmp[l]*dt
                        PE -= Eu_tmp[l]
                # Tu
                for z in range(len(Zr_elev)):
                    if PET[z] > 0.0 :
                        if Tlbot[l] > Zr_elev[z]:
                            Tu_tmpZr[l,z] = evp(Su_tmp[l],Sfc[l]*Tl[l], Sr[l]*Tl[l], PET[z], i, j, n, dt)
                        elif Tltop[l] > Zr_elev[z] :
                            PETc = PET[z]*(Tltop[l]-Zr_elev[z])/Tl[l]
                            Tu_tmpZr[l,z] = evp(Su_tmp[l],Sfc[l]*Tl[l], Sr[l]*Tl[l], PETc, i, j, n, dt)
                        Tu_tmp[l] += Tu_tmpZr[l,z]*VEGarea[z]/100
                        PET[z] -= Tu_tmpZr[l,z]
                Su_tmp[l] -= Tu_tmp[l]*dt

            for l in range(nsl):
                Su_pc_tmp[l] = Su_tmp[l]/Tl[l]

        elif DRN > 0.0:
            # Su_tmp from previous time step
            # if first time step, use Su_ini
            Su_tmp = np.zeros([nsl])
            Rexf_tmp = np.zeros([nsl])
            for l in range(nsl-1):
                Su_tmp[l] = Su_ini[l]
            Su_tmp[nsl-1] = self.hnoflo

            # INFILTRATION
            # first soil layer
            Su_tmp[0] += RFe*dt + Ss_ini
            # other soil layer, percolation from previous time step
            for l in range(1,nsl-1):
                if t == 0:
                    Su_tmp[l] += Rp_ini[l-1]*dti
                else:
                    Su_tmp[l] += Rp[t-1,l-1]*dti
            if DRN_ini == 0.0:
                Su_tmp[nsl-2] += Rp_ini[nsl-2]*dti

            # GW DRN
            Su_tmp[nsl-2] += DRN

            # EXFILTRATION
            llst = range(nsl-1)
            llst.reverse()
            for l in llst[:-1]:
                if Su_tmp[l] > Sm[l]*Tl[l]:
                    Rexf_tmp[l] += Su_tmp[l] - Sm[l]*Tl[l]
                    Su_tmp[l-1] += Rexf_tmp[l]
                    Su_tmp[l] = Sm[l]*Tl[l]

            # Ss and Ro
            surfwater_tmp = surfwater(Su_tmp[0],Sm[0]*Tl[0],Ss_max, E0*Ss_ratio, i, j, n, dt)
            Ss_tmp = surfwater_tmp[0]
            Ro_tmp = surfwater_tmp[1]
            Es_tmp = surfwater_tmp[2]
            Rexf_tmp[0] += sum(surfwater_tmp)
            Su_tmp[0] -= (Ss_tmp + dt*(Ro_tmp + Es_tmp))

            # SAT=True indicates saturation overland flow
            for l in llst:
                if ((np.abs(Su_tmp[l] - (Sm[l]*Tl[l])) < 1.0E-7)):
                    HEADS += Tl[l]
                    dtwt -= Tl[l]
                    SAT[l] = True
                else:
                    break

            Rp_tmp = np.zeros([nsl])
            R_tmp = 0.0
            Tu_tmpZr = np.zeros([nsl,len(Zr_elev)])
            Tu_tmp = np.zeros([nsl])
            Eu_tmp = np.zeros([nsl])
            Su_pc_tmp = np.zeros([nsl])
##            # Groundwater transpiration
##            Tg_tmpZr = np.zeros([nsl, len(Zr_elev)])
##            Tg_tmp = 0.0
##            kTu_max = 1.0
            # soil layers
            for l in range(nsl-1):
                # Rp
                if l < (nsl-2):
                    if SAT[l+1] == False:
                        Rp_tmp[l] = perc(Su_tmp[l],Sm[l]*Tl[l],Sfc[l]*Tl[l],Ks[l], Su_tmp[l+1], Sm[l+1]*Tl[l+1], i, j, n, dt)
                        Su_tmp[l] -= Rp_tmp[l]*dt
            for l in range(nsl-1):
                if SAT[l] == False:
                    # Eu
                    if Ss_tmp == 0.0:
                        if PE > 0.0:
                            Eu_tmp[l] = evp(Su_tmp[l],Sfc[l]*Tl[l], Sr[l]*Tl[l], PE, i, j, n, dt)
                            Su_tmp[l] -= Eu_tmp[l]*dt
                            PE -= Eu_tmp[l]
                    # Tu
                    for z in range(len(Zr_elev)):
                        if PET[z] > 0.0 :
                            if Tlbot[l] > Zr_elev[z]:
                                Tu_tmpZr[l,z] = evp(Su_tmp[l],Sfc[l]*Tl[l], Sr[l]*Tl[l], PET[z], i, j, n, dt)
                            elif Tltop[l] > Zr_elev[z] :
                                PETc = PET[z]*(Tltop[l]-Zr_elev[z])/Tl[l]
                                Tu_tmpZr[l,z] = evp(Su_tmp[l],Sfc[l]*Tl[l], Sr[l]*Tl[l], PETc, i, j, n, dt)
                            Tu_tmp[l] += Tu_tmpZr[l,z]*VEGarea[z]/100
                            PET[z] -= Tu_tmpZr[l,z]
                    Su_tmp[l] -= Tu_tmp[l]*dt
##                elif SAT[l] == True:
##                    for z in range(len(Zr_elev)):
##                        if PET[z] > 0.0 :
##                            if HEADS > Zr_elev[z]:
##                                Tg_tmpZr[l,z] = evp(Sm[l]*Tl[l],Sfc[l]*Tl[l], PET[z], i, j, n, dt)
##                                Tg_tmp += Tg_tmpZr[l,z]*VEGarea[z]/100
##                                PET[z] -= Tg_tmpZr[l,z]

            for l in range(nsl-1):
                if Su_tmp[l] == self.hnoflo:
                    Su_pc_tmp[l] = self.hnoflo
                else:
                    #Su_tmp[l] += Sr[l]*Tl[l]
                    Su_pc_tmp[l] = Su_tmp[l]/Tl[l]
                #Sm[l]  += Sr[l]
                #Sfc[l] += Sr[l]

        # GW evaporation, equation 17 of Shah et al 2007, see ref in the __init__
        if Ss_tmp == 0.0:
            if PE > 0.0:
                dtwt /= 10
                y0    = self.paramEg[st]['y0']
                b     = self.paramEg[st]['b']
                dll   = self.paramEg[st]['dll']
                ext_d = self.paramEg[st]['ext_d']
                if dtwt <= dll:
                    Eg_tmp = PE
                elif dtwt < ext_d:
                    Eg_tmp = PE*(y0 + np.exp(-b*(dtwt-dll)))
                else:
                    Eg_tmp = 0.0
                dtwt *= 10
            else:
                Eg_tmp = 0.0
        else:
            Eg_tmp = 0.0

        # Groundwater transpiration
        Tg_tmpZr = np.zeros([nsl, len(Zr_elev)])
        Tg_tmp = 0.0
        kTu_max = 1.0
        for z in range(len(Zr_elev)):
            if HEADS > Zr_elev[z]:
                for l in range(nsl):
                    if Su_pc_tmp[l] <> self.hnoflo:
                        if Su_pc_tmp[l] >= Sr[l]:
                            if Su_pc_tmp[l] <= Sm[l]:
                                kTu = kTu_min[z]+(kTu_max-kTu_min[z])*np.power(1-np.power(np.abs(Su_pc_tmp[l]-Sm[l])/(Sm[l]-Sr[l]),kTu_n[z]),1/kTu_n[z])
                            else:
                                kTu = kTu_max
                        else:
                            kTu = kTu_min[z]
                        Tg_tmpZr[l,z] = Tu_tmpZr[l,z]*(1/kTu-1)
                        if Tg_tmpZr[l,z] > PET[z]:
                            Tg_tmpZr[l,z] = PET[z]
                        PET[z] -= Tg_tmpZr[l,z]
                        Tg_tmp += (Tg_tmpZr[l,z]*VEGarea[z]/100)

        return Es_tmp, Ss_tmp, Ro_tmp, Rp_tmp, Eu_tmp, Tu_tmp, Su_tmp, Su_pc_tmp, Su_ini, R_tmp, Eg_tmp, Tg_tmp, HEADS, dtwt, MB_err, SAT, Rexf_tmp
        del Es_tmp, Ss_tmp, Ro_tmp, Rp_tmp, Eu_tmp, Tu_tmp, Su_tmp, Su_pc_tmp, Su_ini, R_tmp, Eg_tmp, Tg_tmp, dtwt

#####################

    def run(self, i, j, n,
                  nsl, st, slprop, Sm, Sfc, Sr, Su_ini, Ss_ini, Rp_ini, T, Tll_ini, Ks, Ss_max, Ss_ratio,
                  TopAquif, HEADS, HEADS_ini, DRN, DRN_ini, cf,
                  RF, E0, PETveg, RFeveg, PEsoil, VEGarea, Zr,
                  nstp, perlen, dti, hdry,
                  kTu_min, kTu_n):

        # Output initialisation
        Ttotal = len(RF)
        # PET for the vegetation patchwork
        PET_tot = np.zeros([len(PETveg[0])], dtype = float)
        # PE for the remaining bare soil
        PE_tot = np.zeros([Ttotal], dtype = float)
        # RFe for the vegetation patchwork
        RFe_tot = np.zeros([len(RFeveg[0])], dtype = float)
        # vegetation interception (weigthed average patchwork)
        INTER_tot = np.zeros([Ttotal], dtype = np.float)
        # Ponding storage
        Ss = np.zeros([Ttotal], dtype = np.float)
        # Ponding storage change
        dSs = np.zeros([Ttotal], dtype = np.float)
        # Surface runoff (hortonian and saturated overland flow)
        Ro = np.zeros([Ttotal], dtype = np.float)
        # Percolation
        Rp = np.zeros([Ttotal,nsl], dtype = np.float)
        # Exfiltration
        Rexf = np.zeros([Ttotal,nsl], dtype = np.float)
        #Soil moisture storage
        Su = np.zeros([Ttotal,nsl], dtype = np.float)
        #Soil moisture storage in volumetric percent of saturation
        Su_pc = np.zeros([Ttotal,nsl], dtype = np.float)
        #Soil moisture storage changes
        dSu = np.zeros([Ttotal,nsl], dtype = np.float)
        #Total soil moisture storage changes
        dSu_tot = np.zeros([Ttotal], dtype = np.float)
        #Actual evaporation from unsaturated zone
        Eu = np.zeros([Ttotal,nsl], dtype = np.float)
        #Actual transpiration from unsaturated zone
        Tu = np.zeros([Ttotal,nsl], dtype = np.float)
        #Total actual evapotranspiration from unsaturated zone
        ETu_tot = np.zeros([Ttotal], dtype = np.float)
        #Saturation overland flow
        SAT = np.zeros([Ttotal, nsl], dtype = np.int)
        #Actual evapotranspiration from surface
        Es = np.zeros([Ttotal], dtype = np.float)
        # HEADS
        HEADS_corr = np.zeros([Ttotal], dtype = np.float)
        # GW correction
        MB_err = np.zeros([Ttotal], dtype = np.float)
        # MASS BALANCE
        MB = np.zeros([Ttotal], dtype = np.float)
        # MASS BALANCE each soil layer
        MB_l = np.zeros([Ttotal, nsl], dtype = np.float)
        # bare soil GW evaporation
        Eg = np.zeros([Ttotal], dtype = np.float)
        # GW transpiration
        Tg = np.zeros([Ttotal], dtype = np.float)
        # GW recharge
        R = np.zeros([Ttotal], dtype = np.float)
        # GW net recharge
        Rn = np.zeros([Ttotal], dtype = np.float)
        # GW evapotranspiration
        ETg = np.zeros([Ttotal], dtype = np.float)
        # output arrays
        nflux1 = 23
        nflux2 = 8
        results1 = np.zeros([Ttotal,nflux1])
        results2 = np.zeros([Ttotal,nsl,nflux2])

#        if T < 0.05: #correct soil thickness less than 5cm
#            T=0.05
        # conversion from m to mm
        T = T*1000.0
        TopAquif = TopAquif*1000.0
        # elevation of bottom of soil reservoir
        Dbot = TopAquif
        # topography elevation
        Dtop = TopAquif + T

        # thickness of soil layers
        Tl = np.zeros([nsl], dtype=float)
        for l in range(nsl-1):
            Tl[l] = T*slprop[l]
        # elevation of top and bottom of soil layers
        Tltop = np.zeros([nsl], dtype=float)
        Tlbot = np.zeros([nsl], dtype=float)
        for l in range(nsl-1):
            if l==0:
                Tltop[l] = Dtop
                Tlbot[l] = Dtop-Tl[l]
            else:
                Tltop[l] = Tlbot[l-1]
                Tlbot[l] = Tltop[l]-Tl[l]
        Tltop[nsl-1] = Tlbot[nsl-2]

        Zr_elev = []
        for z in range(len(Zr)):
            Zr_elev.append(Dtop - Zr[z]*1000.0)

        dt = float(perlen)/float(nstp)

        # PROCESSING THE WHOLE DATA SET
        for t in range(int(nstp)):    # t: current time step

            # Preprocessing of PET/PE/INTER and RFe
            # for different vegetation
            SOILarea = 100
            for v in range(len(PETveg)):
                if VEGarea[v] != self.hnoflo:
                    RFe_tot[t] += RFeveg[v,t]*VEGarea[v]/100
                    PET_tot[t] += PETveg[v,t]*VEGarea[v]/100
                    SOILarea   -= VEGarea[v]
            RFe_tot[t]   += RF[t]*SOILarea/100
            INTER_tot[t]  = RF[t] - RFe_tot[t]
            PE_tot[t]     = PEsoil[t]*SOILarea/100

            # handle drycell
            if HEADS[t] > (hdry-1E3):
                HEADS_tmp = Dbot - 100000.0
            else:
                HEADS_tmp = HEADS[t]*1000.0
            if HEADS_ini > (hdry-1E3):
                HEADS_ini = Dbot - 100000.0
            else:
                HEADS_ini *= 1000.0
            dtwt = Dtop-HEADS_tmp

            # bottom boundary
            Tlbot[nsl-1] = HEADS_tmp
            Tl[nsl-1] = Tltop[nsl-1] - HEADS_tmp
            if Tl[nsl-1] < 0.0:
                print '\nWARNING!\nHEADS > soil depth, it is recommended to increase DRN conductivity in the MODFLOW ini file.\nCell (i=%d,j=%d), stress period n=%d' % (i,j,n)
                Tl[nsl-1] = 10.0

            # for the first TS, S_ini is expressed in % and has to be converted in mm
            if n == 0 and t == 0:
                Tll_ini = Tl[nsl-1]
                Su_ini = Su_ini * Tl

            if DRN[t] == 0.0:
                # heads below soil bottom
                DRN_tmp = 0.0
            else:
                # heads above soil bottom
                DRN_tmp = DRN[t]*cf*dt  # cbc are expressed in volume/unit time
            DRN_ini = DRN_ini * cf * dti

            # fluxes
            Es_tmp, Ss_tmp, Ro_tmp, Rp_tmp, Eu_tmp, Tu_tmp, Su_tmp, Su_pc_tmp, Su_ini, R_tmp, Eg_tmp, Tg_tmp, HEADS_tmp, dtwt, MB_err_tmp, SAT_tmp, Rexf_tmp = self.flux(RFe_tot[t], PETveg[:,t], PE_tot[t], Su, Rp, Zr_elev, VEGarea, HEADS_tmp, HEADS_ini, Tltop, Tlbot, Tl, Tll_ini, nsl, Sm, Sfc, Sr, Ks, Ss_max, Ss_ratio, t, Su_ini, Rp_ini, DRN_tmp, DRN_ini, Ss_ini, E0[t], dtwt, st, i, j, n, kTu_min, kTu_n, dt, dti)

            # fill the output arrays
            Ss[t] = Ss_tmp
            Ro[t]   = Ro_tmp
            Es[t]   = Es_tmp
            Eg[t]   = Eg_tmp
            Tg[t]   = Tg_tmp
            R[t]    = R_tmp
            HEADS_corr[t] = HEADS_tmp
            MB_err[t] = MB_err_tmp
            Su[t,:]    = Su_tmp[:]
            Su_pc[t,:] = Su_pc_tmp[:]
            Rp[t,:]    = Rp_tmp[:]
            Rexf[t,:]  = Rexf_tmp[:]
            Eu[t,:]    = Eu_tmp[:]
            Tu[t,:]    = Tu_tmp[:]
            SAT[t,:]   = SAT_tmp[:]
            ETg[t] = Eg[t] + Tg[t]
            Rn[t]  = R[t] - ETg[t]
            if (Ss[t] > Ss_ini):
                dSs[t] = (Ss[t] - Ss_ini)/dt
            # compute the water mass balance (MB) in the unsaturated zone
            Rp_in_MB  = 0.0
            Rp_out_MB = 0.0
            Eu_MB    = 0.0
            Tu_MB    = 0.0
            for l in range(nsl):
                Eu_MB     += Eu[t,l]
                Tu_MB     += Tu[t,l]
                if l < (nsl-1):
                    Rp_in_MB  += Rp_ini[l]
                Rp_out_MB += Rp[t,l]
                if Su[t,l] == self.hnoflo:
                    dSu[t,l] = self.hnoflo
                else:
                    if Su_ini[l] == self.hnoflo:
                        dSu[t,l] = -Su[t,l]/dt
                    else:
                        dSu[t,l] = (Su_ini[l] - Su[t,l])/dt
                    dSu_tot[t] += dSu[t,l]
            ETu_tot[t] = Eu_MB + Tu_MB

            # MASS BALANCE COMPUTING
            # surficial soil layer
            l = 0
            MB_l[t,l] = (RFe_tot[t] + Su_ini[l] + Ss_ini + Rexf[t,l+1]) - (Rp[t,l] + Eu[t,l] + Tu[t,l]+ Su[t,l] + Rexf[t,l])
            if DRN_tmp == 0.0:
                # intermediate soil layers
                llst = range(1,nsl-2)
                for l in llst:
                    MB_l[t,l] = (Rp_ini[l-1] + Su_ini[l] + Rexf[t,l+1]) - (Rp[t,l] + Eu[t,l] + Tu[t,l] + Su[t,l] + Rexf[t,l])
                # last soil layer
                l = nsl - 2
                MB_l[t,l] = (Rp_ini[l-1] + Su_ini[l] + Rexf[t,l+1]) - (Rp[t,l] + Eu[t,l] + Tu[t,l] + Su[t,l] + Rexf[t,l])
                # vadose layer
                l = nsl - 1
                if Su[t,l] == self.hnoflo:
                    Su_tmp = 0.0
                else:
                    Su_tmp = Su[t,l]
                if Su_ini[l] == self.hnoflo:
                    Su_ini_tmp = 0.0
                else:
                    Su_ini_tmp = Su_ini[l]
                MB_l[t,l] = (Rp_ini[l-1] + Su_ini_tmp) - (Rp[t,l] + Eu[t,l] + Tu[t,l] + Su_tmp + Rexf[t,l])
            elif DRN_tmp > 0.0:
                # intermediate soil layers
                llst = range(1,nsl-3)
                for l in llst:
                    MB_l[t,l] = (Rp_ini[l-1] + Su_ini[l] + Rexf[t,l+1]) - (Rp[t,l] + Eu[t,l] + Tu[t,l] + Su[t,l] + Rexf[t,l])
                # last soil layer
                l = nsl - 2
                MB_l[t,l] = (Rp_ini[l-1] + Su_ini[l] + DRN_tmp) - (Eu[t,l] + Tu[t,l] + Su[t,l] + Rexf[t,l])
                # vadose layer
                MB_l[t,l] = 0.0
            # total mass balance for the unsaturated zone
            MB[t] = RFe_tot[t] + Ss_ini + dti*(dSu_tot[t] + Rp_in_MB) + DRN_tmp - dt*(Ss[t] + Ro[t] + Es[t] + Eu_MB + Tu_MB + Rp_out_MB)
            # index = {'iRF':0, 'iPET':1, 'iPE':2, 'iRFe':3, 'iSs':4, 'iRo':5, 'iDRN':6, 'iEs':7, 'iMB':8, 'iI':9, 'iE0':10, 'iEg':11, 'iTg':12, 'iR':13, 'iRn':14, 'idSs':15, 'iETg':16, 'iETu':17, 'idSu':18, 'iHEADScorr':19, 'idtwt':20, 'iTll':21, 'iGWcorr':22}
            results1[t,:] = [RF[t], PET_tot[t], PE_tot[t], RFe_tot[t], Ss[t], Ro[t], DRN_tmp/dt, Es[t], MB[t], INTER_tot[t], E0[t], Eg[t], Tg[t], R[t], Rn[t], dSs[t], ETg[t], ETu_tot[t], dSu_tot[t], HEADS_corr[t]/1000.0, -dtwt/1000.0, Tl[nsl-1], MB_err[t]/dt]
            # index_S = {'iEu':0, 'iTu':1,'iSu_pc':2, 'iRp':3, 'idSu':4, 'iSu':5}
            for l in range(nsl):
                results2[t,l,:] = [Eu[t,l], Tu[t,l], Su_pc[t,l], Rp[t,l], dSu[t,l], Su[t,l], SAT[t,l], MB_l[t,l]]
            # initial values for next time step
            dti = dt
            Ss_ini = Ss[t]
            DRN_ini = DRN_tmp / cf / dti
            Tll_ini = Tl[nsl-1]
            Su_ini = Su[t,:]
            Rp_ini = Rp[t,:]
            HEADSini = HEADS[t]

        return results1, results2, Tl[nsl-1]

        del RF, PET_tot, PE_tot, RFe_tot, Ss, Ro, DRN, Es, MB, INTER_tot, E0, Eg, Tg, R, Rn, dSs, ETg, ETu_tot, dSu_tot, HEADS, HEADS_corr, dtwt
        del Eu, Tu, Su_pc, Rp, dSu, Su
        del results1, results2

class SATFLOW:
    """
    SATFLOW: SATurated FLOW
    Calculate water level fluctuations in function of recharge
    _________________________
    INPUTS
            PARAMETERS
                hi
                h0          base level
                RC          Saturated recession constant
                STO         Aquifer Storage capacity
            STATE VARIABLES
                R           Daily recharge
    OUTPUTS
            h               Daily water level
     _________________________
    """

    def run(self, R, hi, h0, RC, STO):
        h1=np.zeros([len(R)], dtype=np.float)
        h_tmp = (hi*1000.0 + R[0]/STO -hi*1000.0/RC)
        h1[0]=h_tmp
        for t in range(1,len(R)):
            h_tmp = h1[t-1] + R[t]/STO -h1[t-1]/RC
            h1[t]=h_tmp

        h=np.zeros([len(R)], dtype=np.float)
        for t in range(0,len(R)):
            h_tmp= (h1[t] + h0*1000.0)/1000.0
            h[t]=h_tmp

        return h
        del R, h1, h_tmp, h

#EOF#