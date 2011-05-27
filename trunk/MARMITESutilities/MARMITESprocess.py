﻿# -*- coding: utf-8 -*-

__author__ = "Alain Francés <frances08512@itc.nl>"
__version__ = "1.0"
__date__ = "November 2010"

import os
import numpy as np
import pylab
import sys

def readFile(ws, fn):
    inputFile = []
    inputFile_fn = os.path.join(ws, fn)
    if os.path.exists(inputFile_fn):
        fin = open(inputFile_fn, 'r')
    else:
        print "File [" + inputFile_fn + "] doesn't exist, verify name and path!"
        sys.exit()
    line = fin.readline().split()
    delimChar = line[0]
    try:
        for line in fin:
            line_tmp = line.split(delimChar)
            if not line_tmp == []:
                if (not line_tmp[0] == '') and (not line_tmp[0] == '\n'):
                    inputFile.append(line_tmp[0])
            else:
                raise NameError('InputFileFormat')
    except NameError:
        print 'Error in file [' + inputFile_fn + '], check format!'
        sys.exit()
    except e:
        print "Unexpected error in file [" + inputFile_fn + "]\n", sys.exc_info()[0]
        sys.exit()
    fin.close()
    del fin
    return inputFile

class PROCESS:
    def __init__(self, MM_ws, MF_ws, nrow, ncol, xllcorner, yllcorner, cellsizeMF, nstp, hnoflo):
        self.MM_ws = MM_ws
        self.MF_ws = MF_ws
        self.nrow= nrow
        self.ncol= ncol
        self.xllcorner= xllcorner
        self.yllcorner=yllcorner
        self.cellsizeMF=cellsizeMF
        self.nstp=nstp
        self.hnoflo=hnoflo

    ######################

    def inputEsriAscii(self, grid_fn, datatype):

        grid_fn=os.path.join(self.MM_ws,grid_fn)

        grid_out=np.zeros([self.nrow,self.ncol], dtype = datatype)

        grid_out=self.convASCIIraster2array(grid_fn,grid_out)
        return grid_out
        del grid_out

    ######################

    def convASCIIraster2array(self, filenameIN, arrayOUT):
        '''
        Read ESRI/MODFLOW ASCII file and convert to numpy array
        '''

        # Load the grid files
        if os.path.exists(filenameIN):
            fin = open(filenameIN, 'r')
        else:
            raise ValueError, "The file %s doesn't exist!!!" % filenameIN
    #        fout = open(outfile, 'w')

        # test if it is ESRI ASCII file or PEST grid
        line = fin.readline().split()
        testfile = line[0]
        if isinstance(testfile, str):
            # Read the header
            ncol_tmp = int(line[1])
            line = fin.readline().split()
            nrow_tmp = int(line[1])
            line = fin.readline().split()
            xllcorner_tmp = float(line[1])
            line = fin.readline().split()
            yllcorner_tmp = float(line[1])
            line = fin.readline().split()
            cellsizeEsriAscii = float(line[1])
            line = fin.readline().split()
            NODATA_value = float(line[1])
        elif isinstance(testfile, float):
            ncol_tmp = int(line[0])
            nrow_tmp = int(line[1])

        # Process the file
#        print "\nConverting %s to np.array..." % (filenameIN)
        for row in range(nrow_tmp):
        #   if (row % 100) == 0: print ".",
            for col in range(ncol_tmp):
                # Get new data if necessary
                if col == 0: line = fin.readline().split()
                if line[col] == NODATA_value:
                    arrayOUT[row,col] = self.hnoflo
                else:
                    arrayOUT[row,col] = line[col]

        # verify grid consistency between MODFLOW and ESRI ASCII
        if arrayOUT.shape[0] != self.nrow or arrayOUT.shape[1] != self.ncol or self.cellsizeMF != cellsizeEsriAscii:
            raise BaseException, "\nERROR! MODFLOW grid anf the ESRI ASCII grid from file %s don't correspond!.\nCheck the cell size and the number of rows, columns and cellsize." % filenameIN

        fin.close()
        del line, fin

        return arrayOUT
        del arrayOUT

    ######################

    def inputTS(self, NMETEO, NVEG, NSOIL,
                inputDate_fn, inputZON_TS_RF_fn,
                inputZON_TS_PET_fn, inputZON_TS_RFe_fn,
                inputZON_TS_PE_fn, inputZON_TS_E0_fn, MFtime_fn = None
                ):   #IRR_fn

        ntotstp = int(sum(self.nstp))

        # READ date of input files (RF and PET)
        inputDate_fn=os.path.join(self.MM_ws, inputDate_fn)
        if os.path.exists(inputDate_fn):
            inputDate=np.loadtxt(inputDate_fn, dtype = str)
            inputDate = inputDate[:,0]
            inputDate = pylab.datestr2num(inputDate)
            for i in range(1,len(inputDate)):
                #__________________Check date consistency________________#
                difDay=inputDate[i]-inputDate[i-1]
                if (difDay !=1.0):
                    print 'DifDay = ' + str(difDay)
                    raise ValueError, 'The dates of the input data (RF and PET) are not sequencial, check your daily time step!\nError in date %s ' % str(inputDate[i])
        else:
            raise ValueError, "\nThe file %s doesn't exist!!!" % inputDate_fn
        if MFtime_fn == None:
                if len(inputDate) <> ntotstp:
                  raise ValueError, 'The number of time steps in MF (%i) is not the same as the number of days (%i) of the input data (RF and PET).\n' % (ntotstp, int(len(inputDate)))
        else:
            if ntotstp > len(inputDate):
                print 'ERROR!\nThere is more time steps than days in your model, too inneficient!\nChange your parameters in the MODFLOW ini file.'
                sys.exit()

        # READ input ESRI ASCII rasters vegetation
        gridVEGarea_fn=[]
        for v in range(NVEG):
            gridVEGarea_fn.append(os.path.join(self.MM_ws,'inputVEG' + str(v+1)+'area.asc'))
        gridVEGarea=np.zeros([NVEG,self.nrow,self.ncol], dtype=float)
        for v in range(NVEG):
            gridtmp=np.zeros([self.nrow,self.ncol], dtype=float)
            gridVEGarea[v,:,:]=self.convASCIIraster2array(gridVEGarea_fn[v],gridtmp)

        # READ RF for each zone
        RF_fn=os.path.join(self.MM_ws, inputZON_TS_RF_fn)
        if os.path.exists(RF_fn):
            RF = np.loadtxt(RF_fn)
        else:
            raise ValueError, "\nThe file %s doesn't exist!!!" % RF_fn
        RFzonesTS=np.zeros([NMETEO,sum(self.nstp)], dtype=float)
        for n in range(NMETEO):
            for t in range(ntotstp):
                RFzonesTS[n,t]=RF[n*ntotstp+t]

        E0_fn=os.path.join(self.MM_ws, inputZON_TS_E0_fn)
        if os.path.exists(E0_fn):
            E0 = np.loadtxt(E0_fn)
        else:
            raise ValueError, "\nThe file %s doesn't exist!!!" % E0_fn
        E0zonesTS=np.zeros([NMETEO,sum(self.nstp)], dtype=float)
        for n in range(NMETEO):
            for t in range(ntotstp):
                E0zonesTS[n,t]=E0[n*ntotstp+t]

        ### READ IRR for each zone
        ##IRR_fn=os.path.join(self.MM_ws,IRR_fn)
        ##if os.path.exists(IRR_fn):
        ##    IRR = np.loadtxt(IRR_fn)
        ##else:
        ##    raise ValueError, "\nThe file %s doesn't exist!!!" % IRR_fn
        ##IRRzonesnumb=int(IRR[0])
        ##IRRzones=np.zeros([IRRzonesnumb,sum(dis.self.nstp)], dtype=float)
        ##for i in range(IRRzonesnumb):
        ##    for j in range(sum(dis.self.nstp)):
        ##        IRRzones[i,j]=IRR[i*sum(dis.self.nstp)+j+1]


        # READ PET for each zone and each vegetation
        PET_fn = os.path.join(self.MM_ws, inputZON_TS_PET_fn)
        if os.path.exists(PET_fn):
            PETtmp = np.loadtxt(PET_fn)
        else:
            raise ValueError, "\nThe file %s doesn't exist!!!" % PET_fn
        PETvegzonesTS=np.zeros([NMETEO,NVEG,ntotstp], dtype=float)
        for n in range(NMETEO):
            for v in range(NVEG):
                for t in range(ntotstp):
                    PETvegzonesTS[n,v,t]=PETtmp[t+(n*NVEG+v)*ntotstp]
                    #structure is [number of zones, number of vegetation type, time]
        PETvegzonesTS=np.asarray(PETvegzonesTS)

        # READ RFe for each zone and each vegetation
        RFe_fn = os.path.join(self.MM_ws, inputZON_TS_RFe_fn)
        if os.path.exists(RFe_fn):
            RFetmp = np.loadtxt(RFe_fn)
        else:
            raise ValueError, "\nThe file %s doesn't exist!!!" % RFe_fn
        RFevegzonesTS=np.zeros([NMETEO,NVEG,ntotstp], dtype=float)
        for n in range(NMETEO):
            for v in range(NVEG):
                for t in range(ntotstp):
                    RFevegzonesTS[n,v,t]=RFetmp[t+(n*NVEG+v)*ntotstp]
                    #structure is [number of zones, number of vegetation type, time]
        RFevegzonesTS=np.asarray(RFevegzonesTS)


        # READ PE for each zone and each soil
        PE_fn = os.path.join(self.MM_ws, inputZON_TS_PE_fn)
        if os.path.exists(PE_fn):
            PEtmp = np.loadtxt(PE_fn)
        else:
            raise ValueError, "\nThe file %s doesn't exist!!!" % PE_fn
        PEsoilzonesTS=np.zeros([NMETEO,NSOIL,ntotstp], dtype=float)
        for n in range(NMETEO):
            for v in range(NSOIL):
                for t in range(ntotstp):
                    PEsoilzonesTS[n,v,t]=PEtmp[t+(n*NSOIL+v)*ntotstp]
                    #structure is [number of zones, number of vegetation type, time]
        PEsoilzonesTS=np.asarray(PEsoilzonesTS)

        return gridVEGarea, RFzonesTS, E0zonesTS, PETvegzonesTS, RFevegzonesTS, PEsoilzonesTS, inputDate
        del NMETEO, NVEG, NSOIL, inputDate_fn, inputZON_TS_RF_fn, inputZON_TS_PET_fn, inputZON_TS_RFe_fn, inputZON_TS_PE_fn,inputZON_TS_E0_fn
        del gridVEGarea, RFzonesTS, E0zonesTS, PETvegzonesTS, RFevegzonesTS, PEsoilzonesTS, inputDate

    ######################

    def inputSoilParam(self, SOILparam_fn, NSOIL):

        # Soils parameter initialisation
        nam_soil=[]
        nsl=[]
        st=[]
        slprop=[]
        Sm=[]
        Sfc=[]
        Sr=[]
        Si=[]
        Ks=[]

        # soil parameters file
        SOILparam_fn=os.path.join(self.MM_ws,SOILparam_fn)
        if os.path.exists(SOILparam_fn):
            fin = open(SOILparam_fn, 'r')
        else:
            raise ValueError, "\nThe file %s doesn't exist!!!" % SOILparam_fn
        line = fin.readline().split()
        delimChar = line[0]
        inputFile = []
        try:
            for line in fin:
                line_tmp = line.split(delimChar)
                if not line_tmp == []:
                    if (not line_tmp[0] == '') and (not line_tmp[0] == '\n'):
                        inputFile.append(line_tmp[0])
                else:
                    raise NameError('InputFileFormat')
        except NameError:
            raise ValueError, 'Error in the input file, check format!\n'

        SOILzones=int(int(inputFile[0]))
        if SOILzones>NSOIL:
            print '\nWARNING!\n' + str(SOILzones) + ' soil parameters groups in file [' + SOILparam_fn + ']\n Only ' + str(NSOIL) + ' PE time serie(s) found.'
        # trick to initialise the reading position in the next loop
        nsl.append(0)
        for i in range(SOILzones):
            nsl.append(int(inputFile[i+1]))
            if nsl[i+1]<2:
                raise InputError, '\nERROR!\nThe model requires at least one soil layer and one layer in the unsaturated zone.\nMARMITEs only found %2d layer in soil %s' % (nsl[i+1],nam_soil[z])

        # soil parameter definition for each soil type
        nslst = SOILzones+1
        nam_soil=[]
        st=[]
        for z in range(SOILzones):
            nam_soil.append(inputFile[nslst].strip())
            nslst += 1
            st.append(inputFile[nslst].strip())
            nslst += 1
            slprop.append([])
            Sm.append([])
            Sfc.append([])
            Sr.append([])
            Si.append([])
            Ks.append([])
            for ns in range(nsl[z+1]):
                slprop[z].append(float(inputFile[nslst]))
                nslst += 1
                Sm[z].append(float(inputFile[nslst]))
                nslst += 1
                Sfc[z].append(float(inputFile[nslst]))
                nslst += 1
                Sr[z].append(float(inputFile[nslst]))
                nslst += 1
                Si[z].append(float(inputFile[nslst]))
                nslst += 1
                Ks[z].append(float(inputFile[nslst]))
                nslst += 1
                if not(Sm[z]>Sfc[z]>Sr[z] and Sm[z]>=Si[z]>=Sr[z]):
                    raise ValueError, '\nERROR!\nSoils parameters are not valid!\nThe conditions are Sm>Sfc>Sr and Sm>Si>Sr!'
            if sum(slprop[z][0:nsl[z+1]-1])>1:
                raise ValueError, '\nERROR!\nThe sum of the soil layers proportion of %s is >1!\nCorrect your soil data input!\n' % nam_soil[z]
            if sum(slprop[z][0:nsl[z+1]-1])<1:
                raise ValueError, '\nERROR!\nThe sum of the soil layers proportion of %s is <1!\nCorrect your soil data input!\n' % nam_soil[z]

        return nsl[1:len(nsl)], nam_soil, st, slprop, Sm, Sfc, Sr, Si, Ks
        del nsl, nam_soil, st, slprop, Sm, Sfc, Sr, Si, Ks

    ######################

    def inputObs(self, inputObs_fn, inputObsHEADS_fn, inputObsSM_fn, inputDate, _nslmax, nlay,       MFtime_fn = None):
        '''
        observations cells for soil moisture and heads (will also compute SATFLOW)
        '''

        # read coordinates and SATFLOW parameters
        filenameIN = os.path.join(self.MM_ws,inputObs_fn)
        if os.path.exists(filenameIN):
            fin = open(filenameIN, 'r')
            lines = fin.readlines()
            fin.close()
        else:
            raise BaseException, "The file %s doesn't exist!!!" % filenameIN

        # define a dictionnary of observations,  format is: Name (key) x y i j hi h0 RC STO
        obs = {}
        for i in range(1,len(lines)):
            line = lines[i].split()
            name = line[0]
            x = float(line[1])
            y = float(line[2])
            lay = float(line[3])
            try:
                hi  = float(line[4])
                h0  = float(line[5])
                RC  = float(line[6])
                STO = float(line[7])
            except:
                hi = h0 = RC = STO =  self.hnoflo
            # verify if coordinates are inside MODFLOW grid
            if x < self.xllcorner or \
               x > (self.xllcorner+self.ncol*self.cellsizeMF) or \
               y < self.yllcorner or \
               y > (self.yllcorner+self.nrow*self.cellsizeMF):
                   raise BaseException, 'The coordinates of the observation point %s are not inside the MODFLOW grid' % name
            if lay > nlay or lay < 1:
                lay = 0
                print 'WARNING!\nLayer %s of observation point %s is not valid (corrected to layer 1)!\nCheck your file %s (layer number should be between 1 and the number of layer ofthe MODFLOW model, in this case %s).' % (lay, name, inputObs_fn, nlay)
            else:
                lay = lay - 1
            # compute the cordinates in the MODFLOW grid
            #TODO use the PEST utilities for space extrapolation
            i = self.nrow - np.ceil((y-self.yllcorner)/self.cellsizeMF)
            j = np.ceil((x-self.xllcorner)/self.cellsizeMF) - 1
            obs[name] = {'x':x,'y':y,'i': i, 'j': j, 'lay': lay, 'hi':hi, 'h0':h0, 'RC':RC, 'STO':STO}

        outpathname=[]
        #  read obs time series
        for o in range(len(obs.keys())):
            outpathname.append(os.path.join(self.MM_ws,'output'+obs.keys()[o]+'.txt'))
        obs_h=[]
        obs_sm=[]
        for o in range(len(obs.keys())):
            obsh_fn=os.path.join(self.MM_ws, inputObsHEADS_fn + '_' + obs.keys()[o] +'.txt')
            obssm_fn=os.path.join(self.MM_ws, inputObsSM_fn + '_' + obs.keys()[o] + '.txt')
            obs_h.append(self.verifObs(inputDate, obsh_fn, obsnam = obs.keys()[o], MFtime_fn = MFtime_fn))
            obs_sm.append(self.verifObs(inputDate, obssm_fn, _nslmax, obsnam = obs.keys()[o], MFtime_fn = MFtime_fn))

        return obs, outpathname, obs_h, obs_sm
        del inputObs_fn, inputObsHEADS_fn, inputObsSM_fn, inputDate, _nslmax
        del obs, outpathname, obs_h, obs_sm

    ######################

    def verifObs(self, inputDate, filename, _nslmax = 0, obsnam = 'unknown location', MFtime_fn = None):
        '''
        Import and process data and parameters
        '''

        if os.path.exists(filename):
            try:
                obsData=np.loadtxt(filename, dtype = str)
                obsDate = pylab.datestr2num(obsData[:,0])
                obsValue = []
                for l in range(1,len(obsData[0])):
                    obsValue.append(obsData[:,l].astype(float))
                if len(obsValue)<_nslmax:
                    for l in range(_nslmax-len(obsValue)):
                        obsValue.append(self.hnoflo)
            except:
                raise ValueError, '\nERROR!\n Format of observation file uncorrect!\n%s' % filename
            if MFtime_fn == None:
                if obsDate[0]<inputDate[0]:
                    print '\nWARNING!\n Observation data starting before RF and PET at %s,\n these obs data will not be plotted correctly'
                if len(inputDate)<len(obsDate):
                    print '\nWARNING!\n There is more observation data than RF and PET data at %s,\n these obs data will not be plotted correctly' % 1
            obsOutput = np.zeros([len(obsValue),len(inputDate)], dtype=float)
            for l in range(len(obsValue)):
                if not isinstance(obsValue[l], float):
                    j=0
                    for i in range(len(inputDate)):
                        if j<len(obsDate):
                            if inputDate[i]==obsDate[j]:
                                obsOutput[l,i]=obsValue[l][j]
                                j += 1
                            else:
                                obsOutput[l,i]=self.hnoflo
                        else:
                            obsOutput[l,i]=self.hnoflo
                else:
                    obsOutput[l,:] = np.ones([len(inputDate)])*self.hnoflo
        else:
            for i in range(len(inputDate)):
                for l in range(len(obsValue)):
                    obsOutput[l,i]=self.hnoflo

        return obsOutput
        del inputDate, obsOutput

    ######################

    def outputEAgrd(self, outFile_fn, outFolder = []):

        if outFolder == []:
            outFolder = self.MM_ws

        outFile=open(os.path.join(outFolder, outFile_fn), 'w')

        outFile=self.writeHeaderESRIraster(outFile)

        return outFile
        del outFile

    ######################

    def writeHeaderESRIraster(self, file_asc):
        '''
        Write ESRI ASCII raster header
        '''
        file_asc.write('ncols  ' + str(self.ncol)+'\n' +
                       'nrows  '  + str(self.nrow)+'\n' +
                       'xllcorner  '+ str(self.xllcorner)+'\n' +
                        'yllcorner  '+ str(self.yllcorner)+'\n' +
                        'cellsize   '+ str(self.cellsizeMF)+'\n' +
                        'NODATA_value  '+ str(self.hnoflo)+'\n')
        return file_asc
        del file_asc

    ######################

    def ExportResultsMM(self, i, j, inputDate, _nslmax, results, index, results_S, index_S, DRN, RCH, WEL, h_satflow, heads_MF, obs_h, obs_S, outFileExport, obsname):
        """
        Export the processed data in a txt file
        INPUTS:      output fluxes time series and date
        OUTPUT:      output.txt
        """
        for t in range(len(inputDate)):
            year='%4d'%pylab.num2date(inputDate[t]).year
            month='%02d'%pylab.num2date(inputDate[t]).month
            day='%02d'%pylab.num2date(inputDate[t]).day
            date=(day+"/"+month+"/"+year)
            # header='Date,RF,E0,PET,PE,RFe,Inter,'+Eu_str+Tu_str+'Eg,Tg,ETg,WEL_MF,Es,'+S_str+Spc_str+dS_str+'dPOND,POND,Ro,SEEPAGE,DRN_MF,'+Rp_str+'R,Rn,R_MF,hSATFLOW,hMF,hmeas,' + Smeasout + 'MB\n'
            Sout = ''
            Spcout = ''
            dSout = ''
            Rpout=''
            Euout=''
            Tuout=''
            Smeasout = ''
            for l in range(_nslmax):
                Sout = Sout + str(results_S[t,i,j,l,index_S.get('iS')]) + ','
                Spcout = Spcout + str(results_S[t,i,j,l,index_S.get('iSpc')]) + ','
                dSout = dSout + str(results_S[t,i,j,l,index_S.get('idS')]) + ','
                Rpout = Rpout + str(results_S[t,i,j,l,index_S.get('iRp')]) + ','
                Euout = Euout + str(results_S[t,i,j,l,index_S.get('iEu')]) + ','
                Tuout = Tuout + str(results_S[t,i,j,l,index_S.get('iTu')]) + ','
                try:
                    Smeasout = Smeasout + str(obs_S[t,l]) + ','
                except:
                    Smeasout = Smeasout + str(self.hnoflo) + ','
            out_date = pylab.num2date(inputDate[t]).isoformat()[:10]
            out1 = '%.8f,%.8f,%.8f,%.8f,%.8f,%.8f,' % (results[t,i,j,index.get('iRF')], results[t,i,j,index.get('iE0')],results[t,i,j,index.get('iPET')],results[t,i,j,index.get('iPE')],results[t,i,j,index.get('iRFe')],results[t,i,j,index.get('iINTER')])
            out2 = '%.8f,%.8f,%.8f,%.8f,%.8f,' % (results[t,i,j,index.get('iEg')], results[t,i,j,index.get('iTg')],results[t,i,j,index.get('iETg')], WEL[t], results[t,i,j,index.get('iEs')])
            out3 = '%.8f,%.8f,%.8f,%.8f,%.8f,' % (results[t,i,j,index.get('idPOND')],results[t,i,j,index.get('iPOND')],results[t,i,j,index.get('iRo')],results[t,i,j,index.get('iSEEPAGE')],DRN[t])
            out4 = '%.8f,%.8f,%.8f,%.8f,%.8f,%.8f,' % (results[t,i,j,index.get('iR')], results[t,i,j,index.get('iRn')], RCH[t], h_satflow[t],heads_MF[t],obs_h[t])
            out5 = '%.8f' % (results[t,i,j,index.get('iMB')])
            out_line =  out_date, ',', out1, Euout, Tuout, out2, Sout, Spcout, dSout, out3, Rpout, out4, Smeasout, out5, '\n'
            for l in out_line:
                outFileExport.write(l)
        del i, j, inputDate, _nslmax, results, index, results_S, index_S, DRN, RCH, WEL, h_satflow, heads_MF, obs_h, obs_S, outFileExport, obsname

    def ExportResultsPEST(self, i, j, inputDate, _nslmax, heads_MF, obs_h, obs_S, outPESTheads, outPESTsm, obsname, results_S = None, index_S = None):
        """
        Export the processed data in a txt file
        INPUTS:      output fluxes time series and date
        OUTPUT:      output.txt
        """
        for t in range(len(inputDate)):
            year='%4d'%pylab.num2date(inputDate[t]).year
            month='%02d'%pylab.num2date(inputDate[t]).month
            day='%02d'%pylab.num2date(inputDate[t]).day
            date=(day+"/"+month+"/"+year)
            if obs_h[t]!=self.hnoflo:
                obs_h_tmp = str(obs_h[t])
                outPESTheads.write(obsname.ljust(14,' ')+ date.ljust(14,' ')+ '00:00:00        '+ str(heads_MF[t])+ '    \n')
            # TODO export for all soil layers (currently only the SM computed for the first layer is exported)
            if results_S <> None:
                if obs_S[0,t]!=self.hnoflo:
                    Smeasout = ''
                    for l in range (_nslmax):
                        outPESTsm.write((obsname+'SM_l'+str(l+1)).ljust(14,' ')+ date.ljust(14,' ')+ '00:00:00        '+ str(results_S[t,i,j,l,index_S.get('iSpc')]) + '    \n')

# EOF