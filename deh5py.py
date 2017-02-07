import matplotlib.pyplot as plt
import numpy as np
import h5py


M = h5py.File('company_data.hdf5')

for label in M.keys():
	exec('%s = M["%s"][:]' % (label, label))

plt.figure(1)
plt.plot(TIME_StartTime, ACTR_fSat0)
plt.hold('on')
plt.plot(TIME_StartTime, ACTR_fSat1)
plt.plot(TIME_StartTime, -np.array(CTD1_eR2)*np.array(CTD2_kR2))
plt.plot(TIME_StartTime, -CTD1_eq*CTD2_kRate2)
plt.plot(TIME_StartTime,FOMO_myInt, 'x')
plt.plot(TIME_StartTime,CTD5_MyFF)
plt.plot(TIME_StartTime,FOMO_my)
plt.grid('on')

plt.show()
"""
print(M.keys())
plt.figure(1)
plt.plot(M["TIME_StartTime"][:], M["ACTR_fSat0"][:])
plt.hold('on')
plt.plot(M["TIME_StartTime"][:], M["ACTR_fSat1"][:])
plt.plot(M["TIME_StartTime"][:], -M["CTD1_eR2"][:]*M["CTD2_kR2"][:])
plt.plot(M["TIME_StartTime"][:], -M["CTD1_eq"][:]*M["CTD2_kRate2"][:])
plt.plot(M["TIME_StartTime"][:],M["FOMO_myInt"][:], 'x')
plt.plot(M["TIME_StartTime"][:],M["CTD5_MyFF"][:])
plt.plot(M["TIME_StartTime"][:],M["FOMO_my"][:])
plt.grid('on')
plt.show()
"""
