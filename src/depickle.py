import cPickle as pickle
import matplotlib.pyplot as plt
import numpy as np
from sdlog2_pp import SDLog2Parser

with open('company_data.pkl', 'rb') as input:
	parser = pickle.load(input)


for label in parser.csv_columns:
	tmp_name = label.split('_')
	name = tmp_name[0] + '_' + tmp_name[-1]
	exec("%s = %s" % (name, parser.log_data[label]))
	parser.log_data[label] = np.array(parser.log_data[label])

#plt.plot(parser.log_data['CTD1_reg'])
#plt.show()

#Plot various moment contributions to pitching moment, flap saturations
#graph ACTR.fSat0 ACTR.fSat1 -CTD1.eR2*CTD2.kR2 -CTD1.eq*CTD2.kRate2 FOMO.myInt CTD5.MyFF FOMO.my

#Plot pitch, pitch SP and longitudnal velocities
#graph LPOS.Z ATT.Pitch ATSP.PitchSP LPOS.VX*cos(ATT.Yaw)+LPOS.VY*sin(ATT.Yaw) LPSP.VX*cos(ATT.Yaw)+LPSP.VY*sin(ATT.Yaw) LPOS.VX LPOS.VY ATT.Yaw

#Plot various throttle/force contributions to pitch setpoint
#graph MPCD.t1*cos(ATT.Yaw)+MPCD.t2*sin(ATT.Yaw) MPCD.tI1*cos(ATT.Yaw)+MPCD.tI2*sin(ATT.Yaw) -MPCD.dC
#plt.plot(parser.log_data['TIME_StartTime'],parser.log_data['ACTR_fSat0'])
#plt.plot(parser.log_data['TIME_StartTime'], parser.log_data['ACTR_fSat0'])
#plt.hold('on')
#plt.plot(parser.log_data['TIME_StartTime'], parser.log_data['ACTR_fSat1'])
#plt.plot(parser.log_data['TIME_StartTime'], -parser.log_data['CTD1_eR2']*parser.log_data['CTD2_kR2'])
#plt.plot(parser.log_data['TIME_StartTime'], -parser.log_data['CTD1_eq']*parser.log_data['CTD2_kRate2'])
#plt.plot(parser.log_data['TIME_StartTime'], parser.log_data['FOMO_myInt'])
#plt.plot(parser.log_data['TIME_StartTime'], parser.log_data['CTD5_MyFF'])
#plt.plot(parser.log_data['TIME_StartTime'], parser.log_data['FOMO_my'])
#plt.grid('on')
#plt.show()

plt.figure(1)
plt.plot(TIME_StartTime, ACTR_fSat0)
plt.hold('on')
plt.plot(TIME_StartTime, ACTR_fSat1)
plt.plot(TIME_StartTime, -np.array(CTD1_eR2)*np.array(CTD2_kR2))
plt.plot(TIME_StartTime, -np.array(CTD1_eq)*np.array(CTD2_kRate2))
plt.plot(TIME_StartTime,FOMO_myInt, 'x')
plt.plot(TIME_StartTime,CTD5_MyFF)
plt.plot(TIME_StartTime,FOMO_my)
plt.grid('on')

plt.show()
