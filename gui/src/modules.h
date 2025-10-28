#ifndef MODULES_H
#define MODULES_H

#include "archongui.h"
#include "archon.h"

class TArchonGUI;

class TModule : public QObject
{
	Q_OBJECT
public:
	TModule(TArchonGUI *parent, QString key, int slot);
	virtual void createUI() = 0;
	virtual void setClocks(const QVariantMap& map) = 0;
	virtual void getClocks(QVariantMap& map) = 0;
	virtual bool usesClocks() = 0;
	virtual void parseStatus(const RMap &data) = 0;
	virtual void parseUI() = 0;
	virtual void updateUI() = 0;
	QString key;
	int slot;
public slots:
protected:
	TArchonGUI *parent;
};

class DRIVER : public TModule
{
	Q_OBJECT
public:
	DRIVER(TArchonGUI *parent, QString key, int slot);
	virtual void createUI();
	virtual void setClocks(const QVariantMap& map);
	virtual void getClocks(QVariantMap& map);
	virtual bool usesClocks() {return true;}
	virtual void parseStatus(const RMap &/*data*/) {}
	virtual void parseUI();
	virtual void updateUI();
public slots:
	void clockChanged();
	void copyClocks();
	void pasteClocks();
	void apply();
private:
	int build;
	int backplane_build;
	static const int DRIVER_COUNT = 8;
	QLineEdit *leLabels[DRIVER_COUNT];
	QLineEdit *leFastSlewRates[DRIVER_COUNT];
	QLineEdit *leSlowSlewRates[DRIVER_COUNT];
	QCheckBox *cbEnabled[DRIVER_COUNT];
	QLineEdit *leSource[DRIVER_COUNT];
	QLabel *lRefLabels[DRIVER_COUNT];
	QLineEdit *leLevels[DRIVER_COUNT];
	QCheckBox *cbSlews[DRIVER_COUNT];
	QCheckBox *cbKeeps[DRIVER_COUNT];
};

class DRIVERX : public TModule
{
	Q_OBJECT
public:
	DRIVERX(TArchonGUI *parent, QString key, int slot);
	virtual void createUI();
	virtual void setClocks(const QVariantMap& map);
	virtual void getClocks(QVariantMap& map);
	virtual bool usesClocks() {return true;}
	virtual void parseStatus(const RMap &/*data*/) {}
	virtual void parseUI();
	virtual void updateUI();
public slots:
	void clockChanged();
	void copyClocks();
	void pasteClocks();
	void apply();
private:
	int build;
	int backplane_build;
	static const int DRIVERX_COUNT = 12;
	QLineEdit *leLabels[DRIVERX_COUNT];
	QLineEdit *leFastSlewRates[DRIVERX_COUNT];
	QLineEdit *leSlowSlewRates[DRIVERX_COUNT];
	QCheckBox *cbEnabled[DRIVERX_COUNT];
	QLineEdit *leSource[DRIVERX_COUNT];
	QLabel *lRefLabels[DRIVERX_COUNT];
	QLineEdit *leLevels[DRIVERX_COUNT];
	QCheckBox *cbSlews[DRIVERX_COUNT];
	QCheckBox *cbKeeps[DRIVERX_COUNT];
};

class AD : public TModule
{
	Q_OBJECT
public:
	AD(TArchonGUI *parent, QString key, int slot);
	virtual void createUI();
	virtual void setClocks(const QVariantMap& map);
	virtual void getClocks(QVariantMap& map);
	virtual bool usesClocks() {return true;}
	virtual void parseStatus(const RMap &/*data*/) {}
	virtual void parseUI();
	virtual void updateUI();
public slots:
	void clockChanged();
	void copyClocks();
	void pasteClocks();
	void apply();
	void clearCal();
	void setCal();
private:
	static const int AD_COUNT = 4;
	QLineEdit *leClampHigh;
	QLineEdit *leClampLow;
	QLineEdit *leClamps[4];
	QLineEdit *leCal[8];
	QComboBox *cbGain;
	QCheckBox *cbClamp;
	QCheckBox *cbKeep;
	char rev;
};

class ADF : public TModule
{
	Q_OBJECT
public:
	ADF(TArchonGUI *parent, QString key, int slot);
	virtual void createUI();
	virtual void setClocks(const QVariantMap& map);
	virtual void getClocks(QVariantMap& map);
	virtual bool usesClocks() {return true;}
	virtual void parseStatus(const RMap &/*data*/) {}
	virtual void parseUI();
	virtual void updateUI();
public slots:
	void clockChanged();
	void copyClocks();
	void pasteClocks();
	void apply();
	void clearCal();
	void setCal();
private:
	static const int AD_COUNT = 4;
	QLineEdit *leClampHigh;
	QLineEdit *leClampLow;
	QLineEdit *leClamps[4];
	QLineEdit *leCal[8];
	QCheckBox *cbClamp;
	QCheckBox *cbKeep;
	char rev;
};

class ADX : public TModule
{
	Q_OBJECT
public:
	ADX(TArchonGUI *parent, QString key, int slot);
	virtual void createUI();
	virtual void setClocks(const QVariantMap& map);
	virtual void getClocks(QVariantMap& map);
	virtual bool usesClocks() {return true;}
	virtual void parseStatus(const RMap &/*data*/) {}
	virtual void parseUI();
	virtual void updateUI();
public slots:
	void clockChanged();
	void copyClocks();
	void pasteClocks();
	void apply();
private:
	static const int AD_COUNT = 4;
	QLineEdit *leClampHigh;
	QLineEdit *leClampLow;
	QLineEdit *leClamps[4];
	QCheckBox *cbClamp;
	QCheckBox *cbKeep;
	char rev;
};

class ADLN : public TModule
{
	Q_OBJECT
public:
	ADLN(TArchonGUI *parent, QString key, int slot);
	virtual void createUI();
	virtual void setClocks(const QVariantMap& map);
	virtual void getClocks(QVariantMap& map);
	virtual bool usesClocks() {return true;}
	virtual void parseStatus(const RMap &/*data*/) {}
	virtual void parseUI();
	virtual void updateUI();
public slots:
	void clockChanged();
	void copyClocks();
	void pasteClocks();
	void apply();
	void clearCal();
	void setCal();
private:
	static const int AD_COUNT = 4;
	QLineEdit *leClampHigh;
	QLineEdit *leClampLow;
	QLineEdit *leClamps[4];
	QLineEdit *leCal[8];
	QCheckBox *cbClamp;
	QCheckBox *cbKeep;
	char rev;
};

class ADM : public TModule
{
	Q_OBJECT
public:
	ADM(TArchonGUI *parent, QString key, int slot);
	virtual void createUI();
	virtual void setClocks(const QVariantMap& map);
	virtual void getClocks(QVariantMap& map);
	virtual bool usesClocks() {return false;}
	virtual void parseStatus(const RMap &/*data*/) {}
	virtual void parseUI();
	virtual void updateUI();
public slots:
	void clockChanged();
	void copyClocks();
	void pasteClocks();
private:
	char rev;
};

class LVBIAS : public TModule
{
	Q_OBJECT
public:
	LVBIAS(TArchonGUI *parent, QString key, int slot);
	virtual void createUI();
	virtual void setClocks(const QVariantMap& map);
	virtual void getClocks(QVariantMap& map);
	virtual bool usesClocks() {return true;}
	virtual void parseStatus(const RMap &data);
	virtual void parseUI();
	virtual void updateUI();
public slots:
	void clockChanged();
	void copyClocks();
	void pasteClocks();
	void apply();
	void applyDIO();
private:
	static const int LVLC_COUNT = 24;
	static const int LVHC_COUNT = 6;
	static const int DIO_COUNT = 8;
	int build;
	// LVLC
	QLineEdit *lvlc_label[LVLC_COUNT];
	QLineEdit *lvlc_v_cmd[LVLC_COUNT];
	QLabel *lvlc_v[LVLC_COUNT];
	QLabel *lvlc_i[LVLC_COUNT];
	QLineEdit *lvlc_order[LVLC_COUNT];
	// LVHC
	QLineEdit *lvhc_label[LVHC_COUNT];
	QLineEdit *lvhc_v_cmd[LVHC_COUNT];
	QLineEdit *lvhc_il[LVHC_COUNT];
	QLabel *lvhc_v[LVHC_COUNT];
	QLabel *lvhc_i[LVHC_COUNT];
	QLineEdit *lvhc_order[LVHC_COUNT];
	QCheckBox *lvhc_enable[LVHC_COUNT];
	// DIO
	QLineEdit *leLabels[DIO_COUNT];
	QComboBox *cbSources[DIO_COUNT];
	QLabel *lStatus[DIO_COUNT];
	QComboBox *cbDirections[DIO_COUNT / 2];
	QLabel *lRefLabels[DIO_COUNT];
	QCheckBox *cbStates[DIO_COUNT];
	QCheckBox *cbKeeps[DIO_COUNT];
	QComboBox *cbPower;
	// VCPU
	static const int VCPU_COUNT = 16;
	QPlainTextEdit *teVCPU;
	QLineEdit *leVCPUInReg[VCPU_COUNT];
	QLabel *lVCPUOutReg[VCPU_COUNT];
	// Timing
	QCheckBox *cbBiasCmd;
	QLineEdit *leBiasChannel;
	QLineEdit *leBiasVoltage;
};

class HVBIAS : public TModule
{
	Q_OBJECT
public:
	HVBIAS(TArchonGUI *parent, QString key, int slot);
	virtual void createUI();
	virtual void setClocks(const QVariantMap& map);
	virtual void getClocks(QVariantMap& map);
	virtual bool usesClocks() {return true;}
	virtual void parseStatus(const RMap &data);
	virtual void parseUI();
	virtual void updateUI();
public slots:
	void clockChanged();
	void copyClocks();
	void pasteClocks();
	void apply();
private:
	static const int HVLC_COUNT = 24;
	static const int HVHC_COUNT = 6;
	int build;
	// HVLC
	QLineEdit *hvlc_label[HVLC_COUNT];
	QLineEdit *hvlc_v_cmd[HVLC_COUNT];
	QLabel *hvlc_v[HVLC_COUNT];
	QLabel *hvlc_i[HVLC_COUNT];
	QLineEdit *hvlc_order[HVLC_COUNT];
	// HVHC
	QLineEdit *hvhc_label[HVHC_COUNT];
	QLineEdit *hvhc_v_cmd[HVHC_COUNT];
	QLineEdit *hvhc_il[HVHC_COUNT];
	QLabel *hvhc_v[HVHC_COUNT];
	QLabel *hvhc_i[HVHC_COUNT];
	QLineEdit *hvhc_order[HVHC_COUNT];
	QCheckBox *hvhc_enable[HVHC_COUNT];
	// Timing
	QCheckBox *cbBiasCmd;
	QLineEdit *leBiasChannel;
	QLineEdit *leBiasVoltage;
};

class HEATER : public TModule
{
	Q_OBJECT
public:
	HEATER(TArchonGUI *parent, QString key, int slot);
	virtual void createUI();
	virtual void setClocks(const QVariantMap& map);
	virtual void getClocks(QVariantMap& map);
	virtual bool usesClocks() {return true;}
	virtual void parseStatus(const RMap &data);
	virtual void parseUI();
	virtual void updateUI();
public slots:
	void clockChanged();
	void copyClocks();
	void pasteClocks();
	void apply();
	void applyDIO();
	void enablePlotting();
	void disablePlotting();
	void savePlots();
private:
	static const int DIO_COUNT = 8;
	QLabel *tempa;
	QLabel *tempb;
	QLabel *heaterOutputA;
	QLabel *heaterOutputB;
	QCheckBox *cbEnableA;
	QCheckBox *cbEnableB;
	QCheckBox *cbForceA;
	QCheckBox *cbForceB;
	QLineEdit *HeaterATarget;
	QLineEdit *HeaterBTarget;
	QLineEdit *HeaterAP;
	QLineEdit *HeaterBP;
	QLineEdit *HeaterAI;
	QLineEdit *HeaterBI;
	QLineEdit *HeaterAD;
	QLineEdit *HeaterBD;
	QLineEdit *HeaterAIL;
	QLineEdit *HeaterBIL;
	QLabel *HeaterAPErr;
	QLabel *HeaterBPErr;
	QLabel *HeaterAIErr;
	QLabel *HeaterBIErr;
	QLabel *HeaterADErr;
	QLabel *HeaterBDErr;
	QLineEdit *HeaterAForceLevel;
	QLineEdit *HeaterBForceLevel;
	QLineEdit *HeaterALimit;
	QLineEdit *HeaterBLimit;
	QLineEdit *HeaterUpdateTime;
	QComboBox *TempASensor;
	QComboBox *TempBSensor;
	QComboBox *TempASensorType;
	QComboBox *TempBSensorType;
	QLineEdit *TempALowerLimit;
	QLineEdit *TempAUpperLimit;
	QLineEdit *TempBLowerLimit;
	QLineEdit *TempBUpperLimit;
	QCheckBox *cbHeaterARamp;
	QCheckBox *cbHeaterBRamp;
	QLineEdit *HeaterARampRate;
	QLineEdit *HeaterBRampRate;
	QwtPlot *HPlotA;
	QwtPlotCurve *HCurveA;
	QwtPlotPanner *HPannerA;
	QwtPlotZoomer *HZoomerA;
	QwtPlot *HPlotB;
	QwtPlotCurve *HCurveB;
	QwtPlotPanner *HPannerB;
	QwtPlotZoomer *HZoomerB;
	int temp_t;
	QVector<double> htime;
	QVector<double> htempa;
	QVector<double> htempb;
	bool plottingEnabled;
	QDateTime pollt;
	int build;
	// DIO
	QLineEdit *leLabels[DIO_COUNT];
	QComboBox *cbSources[DIO_COUNT];
	QLabel *lStatus[DIO_COUNT];
	QComboBox *cbDirections[DIO_COUNT / 2];
	QLabel *lRefLabels[DIO_COUNT];
	QCheckBox *cbStates[DIO_COUNT];
	QCheckBox *cbKeeps[DIO_COUNT];
	QComboBox *cbPower;
	// VCPU
	static const int VCPU_COUNT = 16;
	QPlainTextEdit *teVCPU;
	QLineEdit *leVCPUInReg[VCPU_COUNT];
	QLabel *lVCPUOutReg[VCPU_COUNT];
};

class ATLAS : public TModule
{
	Q_OBJECT
public:
	ATLAS(TArchonGUI *parent, QString key, int slot);
	virtual void createUI();
	virtual void setClocks(const QVariantMap& map);
	virtual void getClocks(QVariantMap& map);
	virtual bool usesClocks() {return true;}
	virtual void parseStatus(const RMap &data);
	virtual void parseUI();
	virtual void updateUI();
public slots:
	void clockChanged();
	void copyClocks();
	void pasteClocks();
	void apply();
	void moveMotor1();
	void moveMotor2();
	void moveMotor3();
private:
	static const int RTD_COUNT = 8;
	static const int HALL_COUNT = 3;
	static const int LED_COUNT = 3;
	QComboBox *enable_tec;
	QLabel *tec_enabled;
	QLabel *tec_voltage;
	QLabel *tec_current;
	QComboBox *enable_ion;
	QLabel *ion_enabled;
	QLabel *ion_voltage;
	QLabel *ion_current;
	QLabel *rtd[RTD_COUNT];
	QLabel *hall[HALL_COUNT];
	QComboBox *cbLEDs[LED_COUNT];
	QLabel *vac_reading;
	QLineEdit *motor1;
	QLineEdit *motor2;
	QLineEdit *motor3;
	QCheckBox *cbLED;
	QCheckBox *cbKeep;
};

class HS : public TModule
{
	Q_OBJECT
public:
	HS(TArchonGUI *parent, QString key, int slot);
	virtual void createUI();
	virtual void setClocks(const QVariantMap& map);
	virtual void getClocks(QVariantMap& map);
	virtual bool usesClocks() {return true;}
	virtual void parseStatus(const RMap &data);
	virtual void parseUI();
	virtual void updateUI();
public slots:
	void clockChanged();
	void copyClocks();
	void pasteClocks();
	void apply();
	void applyDIO();
private:
	static const int HS_COUNT = 12;
	QLineEdit *hs_label[HS_COUNT];
	QLineEdit *hs_sequence[HS_COUNT];
	QCheckBox *cbKeeps[HS_COUNT];
	// Mag
	QLineEdit *mag_label[HS_COUNT];
	QLineEdit *mag_v_cmd[HS_COUNT];
	QLabel *mag_v[HS_COUNT];
	QLabel *mag_i[HS_COUNT];
	// Ofs
	QLineEdit *ofs_label[HS_COUNT];
	QLineEdit *ofs_v_cmd[HS_COUNT];
	QLabel *ofs_v[HS_COUNT];
	QLabel *ofs_i[HS_COUNT];
	QLabel *lRefLabels[HS_COUNT];
	// DIO
	static const int DIO_HS_COUNT = 4;
	QLineEdit *leDIOLabels[DIO_HS_COUNT];
	QComboBox *cbDIOSources[DIO_HS_COUNT];
	QLabel *lDIOStatus[DIO_HS_COUNT];
	QComboBox *cbDIODirections[DIO_HS_COUNT];
	QLabel *lDIORefLabels[DIO_HS_COUNT];
	QCheckBox *cbDIOStates[DIO_HS_COUNT];
	QCheckBox *cbDIOKeeps[DIO_HS_COUNT];
	QComboBox *cbDIOPower;
	// VCPU
	static const int VCPU_COUNT = 16;
	QPlainTextEdit *teVCPU;
	QLineEdit *leVCPUInReg[VCPU_COUNT];
	QLabel *lVCPUOutReg[VCPU_COUNT];
};

class LVDS : public TModule
{
	Q_OBJECT
public:
	LVDS(TArchonGUI *parent, QString key, int slot);
	virtual void createUI();
	virtual void setClocks(const QVariantMap& map);
	virtual void getClocks(QVariantMap& map);
	virtual bool usesClocks() {return true;}
	virtual void parseStatus(const RMap &data);
	virtual void parseUI();
	virtual void updateUI();
public slots:
	void clockChanged();
	void copyClocks();
	void pasteClocks();
	void apply();
private:
	static const int LVDS_COUNT = 16;
	QLineEdit *lvds_label[LVDS_COUNT];
	QLineEdit *lvds_state[LVDS_COUNT];
	QCheckBox *cbKeeps[LVDS_COUNT];
	QLabel *lRefLabels[LVDS_COUNT];
	// DIO
	static const int DIO_LVDS_COUNT = 4;
	QLineEdit *leDIOLabels[DIO_LVDS_COUNT];
	QComboBox *cbDIOSources[DIO_LVDS_COUNT];
	QLabel *lDIOStatus[DIO_LVDS_COUNT];
	QComboBox *cbDIODirections[DIO_LVDS_COUNT];
	QLabel *lDIORefLabels[DIO_LVDS_COUNT];
	QCheckBox *cbDIOStates[DIO_LVDS_COUNT];
	QCheckBox *cbDIOKeeps[DIO_LVDS_COUNT];
	QComboBox *cbDIOPower;
	// VCPU
	static const int VCPU_COUNT = 16;
	QPlainTextEdit *teVCPU;
	QLineEdit *leVCPUInReg[VCPU_COUNT];
	QLabel *lVCPUOutReg[VCPU_COUNT];
};

class HEATERX : public TModule
{
	Q_OBJECT
public:
	HEATERX(TArchonGUI *parent, QString key, int slot);
	virtual void createUI();
	virtual void setClocks(const QVariantMap& map);
	virtual void getClocks(QVariantMap& map);
	virtual bool usesClocks() {return true;}
	virtual void parseStatus(const RMap &data);
	virtual void parseUI();
	virtual void updateUI();
public slots:
	void clockChanged();
	void copyClocks();
	void pasteClocks();
	void apply();
	void applyDIO();
	void enablePlotting();
	void disablePlotting();
	void savePlots();
private:
	static const int DIO_COUNT = 8;
	QLineEdit *SensorALabel;
	QLineEdit *SensorBLabel;
	QLineEdit *SensorCLabel;
	QLabel *SensorA;
	QLabel *SensorB;
	QLabel *SensorC;
	QComboBox *SensorAType;
	QComboBox *SensorBType;
	QComboBox *SensorCType;
	QLineEdit *SensorACurrent;
	QLineEdit *SensorBCurrent;
	QLineEdit *SensorCCurrent;
	QLineEdit *SensorALowerLimit;
	QLineEdit *SensorBLowerLimit;
	QLineEdit *SensorCLowerLimit;
	QLineEdit *SensorAUpperLimit;
	QLineEdit *SensorBUpperLimit;
	QLineEdit *SensorCUpperLimit;
	QComboBox *SensorAFilter;
	QComboBox *SensorBFilter;
	QComboBox *SensorCFilter;
	QLabel *HeaterAOutput;
	QLabel *HeaterBOutput;
	QLineEdit *HeaterALabel;
	QLineEdit *HeaterBLabel;
	QCheckBox *cbHeaterAEnable;
	QCheckBox *cbHeaterBEnable;
	QCheckBox *cbHeaterAForce;
	QCheckBox *cbHeaterBForce;
	QLineEdit *HeaterATarget;
	QLineEdit *HeaterBTarget;
	QComboBox *HeaterASensor;
	QComboBox *HeaterBSensor;
	QLineEdit *HeaterAP;
	QLineEdit *HeaterBP;
	QLineEdit *HeaterAI;
	QLineEdit *HeaterBI;
	QLineEdit *HeaterAD;
	QLineEdit *HeaterBD;
	QLineEdit *HeaterAIL;
	QLineEdit *HeaterBIL;
	QLabel *HeaterAPErr;
	QLabel *HeaterBPErr;
	QLabel *HeaterAIErr;
	QLabel *HeaterBIErr;
	QLabel *HeaterADErr;
	QLabel *HeaterBDErr;
	QLineEdit *HeaterAForceLevel;
	QLineEdit *HeaterBForceLevel;
	QLineEdit *HeaterALimit;
	QLineEdit *HeaterBLimit;
	QLineEdit *HeaterUpdateTime;
	QCheckBox *cbHeaterARamp;
	QCheckBox *cbHeaterBRamp;
	QLineEdit *HeaterARampRate;
	QLineEdit *HeaterBRampRate;
	QwtPlot *HPlotA;
	QwtPlotCurve *HCurveA;
	QwtPlotPanner *HPannerA;
	QwtPlotZoomer *HZoomerA;
	QwtPlot *HPlotB;
	QwtPlotCurve *HCurveB;
	QwtPlotPanner *HPannerB;
	QwtPlotZoomer *HZoomerB;
	QwtPlot *HPlotC;
	QwtPlotCurve *HCurveC;
	QwtPlotPanner *HPannerC;
	QwtPlotZoomer *HZoomerC;
	QVector<double> htime;
	QVector<double> htempa;
	QVector<double> htempb;
	QVector<double> htempc;
	bool plottingEnabled;
	QDateTime pollt;
	int build;
	int backplane_build;
	// DIO
	QLineEdit *leLabels[DIO_COUNT];
	QComboBox *cbSources[DIO_COUNT];
	QLabel *lStatus[DIO_COUNT];
	QComboBox *cbDirections[DIO_COUNT / 2];
	QLabel *lRefLabels[DIO_COUNT];
	QCheckBox *cbStates[DIO_COUNT];
	QCheckBox *cbKeeps[DIO_COUNT];
	QComboBox *cbPower;
	// VCPU
	static const int VCPU_COUNT = 16;
	QPlainTextEdit *teVCPU;
	QLineEdit *leVCPUInReg[VCPU_COUNT];
	QLabel *lVCPUOutReg[VCPU_COUNT];
};

class XVBIAS : public TModule
{
	Q_OBJECT
public:
	XVBIAS(TArchonGUI *parent, QString key, int slot);
	virtual void createUI();
	virtual void setClocks(const QVariantMap& map);
	virtual void getClocks(QVariantMap& map);
	virtual bool usesClocks() {return true;}
	virtual void parseStatus(const RMap &data);
	virtual void parseUI();
	virtual void updateUI();
public slots:
	void clockChanged();
	void copyClocks();
	void pasteClocks();
	void apply();
private:
	static const int XV_COUNT = 4;
	int build;
	// Positive biases
	QLineEdit *xvp_label[XV_COUNT];
	QLineEdit *xvp_v_cmd[XV_COUNT];
	QLabel *xvp_v[XV_COUNT];
	QLabel *xvp_i[XV_COUNT];
	QLineEdit *xvp_order[XV_COUNT];
	QCheckBox *xvp_enable[XV_COUNT];
	// Negative biases
	QLineEdit *xvn_label[XV_COUNT];
	QLineEdit *xvn_v_cmd[XV_COUNT];
	QLabel *xvn_v[XV_COUNT];
	QLabel *xvn_i[XV_COUNT];
	QLineEdit *xvn_order[XV_COUNT];
	QCheckBox *xvn_enable[XV_COUNT];
	// Timing
	QCheckBox *cbPBiasCmd;
	QLineEdit *lePBiasChannel;
	QLineEdit *lePBiasVoltage;
	QCheckBox *cbNBiasCmd;
	QLineEdit *leNBiasChannel;
	QLineEdit *leNBiasVoltage;
};

#endif // MODULES_H
