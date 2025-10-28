/****************************************************************************
** Meta object code from reading C++ file 'archongui.h'
**
** Created by: The Qt Meta Object Compiler version 67 (Qt 5.15.3)
**
** WARNING! All changes made in this file will be lost!
*****************************************************************************/

#include <memory>
#include "../../src/archongui.h"
#include <QtCore/qbytearray.h>
#include <QtCore/qmetatype.h>
#if !defined(Q_MOC_OUTPUT_REVISION)
#error "The header file 'archongui.h' doesn't include <QObject>."
#elif Q_MOC_OUTPUT_REVISION != 67
#error "This file was generated using the moc from 5.15.3. It"
#error "cannot be used with the include files from this version of Qt."
#error "(The moc has changed too much.)"
#endif

QT_BEGIN_MOC_NAMESPACE
QT_WARNING_PUSH
QT_WARNING_DISABLE_DEPRECATED
struct qt_meta_stringdata_TArchonGUI_t {
    QByteArrayData data[103];
    char stringdata0[1132];
};
#define QT_MOC_LITERAL(idx, ofs, len) \
    Q_STATIC_BYTE_ARRAY_DATA_HEADER_INITIALIZER_WITH_OFFSET(len, \
    qptrdiff(offsetof(qt_meta_stringdata_TArchonGUI_t, stringdata0) + ofs \
        - idx * sizeof(QByteArrayData)) \
    )
static const qt_meta_stringdata_TArchonGUI_t qt_meta_stringdata_TArchonGUI = {
    {
QT_MOC_LITERAL(0, 0, 10), // "TArchonGUI"
QT_MOC_LITERAL(1, 11, 8), // "openFile"
QT_MOC_LITERAL(2, 20, 0), // ""
QT_MOC_LITERAL(3, 21, 8), // "saveFile"
QT_MOC_LITERAL(4, 30, 12), // "openNiceFile"
QT_MOC_LITERAL(5, 43, 12), // "saveNiceFile"
QT_MOC_LITERAL(6, 56, 9), // "showAbout"
QT_MOC_LITERAL(7, 66, 10), // "testButton"
QT_MOC_LITERAL(8, 77, 8), // "applyAll"
QT_MOC_LITERAL(9, 86, 8), // "applyCDS"
QT_MOC_LITERAL(10, 95, 10), // "loadTiming"
QT_MOC_LITERAL(11, 106, 14), // "loadParameters"
QT_MOC_LITERAL(12, 121, 4), // "test"
QT_MOC_LITERAL(13, 126, 11), // "resetTiming"
QT_MOC_LITERAL(14, 138, 10), // "holdTiming"
QT_MOC_LITERAL(15, 149, 13), // "releaseTiming"
QT_MOC_LITERAL(16, 163, 10), // "fetchFrame"
QT_MOC_LITERAL(17, 174, 5), // "frame"
QT_MOC_LITERAL(18, 180, 8), // "newFrame"
QT_MOC_LITERAL(19, 189, 7), // "powerOn"
QT_MOC_LITERAL(20, 197, 8), // "powerOff"
QT_MOC_LITERAL(21, 206, 6), // "pollOn"
QT_MOC_LITERAL(22, 213, 7), // "pollOff"
QT_MOC_LITERAL(23, 221, 11), // "applySystem"
QT_MOC_LITERAL(24, 233, 14), // "connectClicked"
QT_MOC_LITERAL(25, 248, 12), // "flashClicked"
QT_MOC_LITERAL(26, 261, 13), // "verifyClicked"
QT_MOC_LITERAL(27, 275, 13), // "rebootClicked"
QT_MOC_LITERAL(28, 289, 15), // "warmbootClicked"
QT_MOC_LITERAL(29, 305, 24), // "flashActiveConfigClicked"
QT_MOC_LITERAL(30, 330, 24), // "eraseStoredConfigClicked"
QT_MOC_LITERAL(31, 355, 18), // "flashModuleClicked"
QT_MOC_LITERAL(32, 374, 19), // "verifyModuleClicked"
QT_MOC_LITERAL(33, 394, 4), // "poll"
QT_MOC_LITERAL(34, 399, 10), // "logMessage"
QT_MOC_LITERAL(35, 410, 3), // "msg"
QT_MOC_LITERAL(36, 414, 15), // "progressMessage"
QT_MOC_LITERAL(37, 430, 7), // "newstep"
QT_MOC_LITERAL(38, 438, 8), // "newtotal"
QT_MOC_LITERAL(39, 447, 9), // "msgSystem"
QT_MOC_LITERAL(40, 457, 4), // "RMap"
QT_MOC_LITERAL(41, 462, 4), // "data"
QT_MOC_LITERAL(42, 467, 9), // "msgStatus"
QT_MOC_LITERAL(43, 477, 14), // "msgFrameStatus"
QT_MOC_LITERAL(44, 492, 12), // "msgConnected"
QT_MOC_LITERAL(45, 505, 9), // "connected"
QT_MOC_LITERAL(46, 515, 12), // "stateChanged"
QT_MOC_LITERAL(47, 528, 12), // "clockChanged"
QT_MOC_LITERAL(48, 541, 7), // "stateUp"
QT_MOC_LITERAL(49, 549, 9), // "stateDown"
QT_MOC_LITERAL(50, 559, 8), // "stateAdd"
QT_MOC_LITERAL(51, 568, 11), // "stateDelete"
QT_MOC_LITERAL(52, 580, 14), // "stateDuplicate"
QT_MOC_LITERAL(53, 595, 11), // "zoomInClick"
QT_MOC_LITERAL(54, 607, 10), // "zoom1Click"
QT_MOC_LITERAL(55, 618, 12), // "zoomOutClick"
QT_MOC_LITERAL(56, 631, 12), // "zoomFitClick"
QT_MOC_LITERAL(57, 644, 12), // "imageMouseXY"
QT_MOC_LITERAL(58, 657, 1), // "x"
QT_MOC_LITERAL(59, 659, 1), // "y"
QT_MOC_LITERAL(60, 661, 6), // "sample"
QT_MOC_LITERAL(61, 668, 11), // "plotChanged"
QT_MOC_LITERAL(62, 680, 5), // "hplot"
QT_MOC_LITERAL(63, 686, 5), // "vplot"
QT_MOC_LITERAL(64, 692, 11), // "statChanged"
QT_MOC_LITERAL(65, 704, 2), // "x1"
QT_MOC_LITERAL(66, 707, 2), // "y1"
QT_MOC_LITERAL(67, 710, 2), // "x2"
QT_MOC_LITERAL(68, 713, 2), // "y2"
QT_MOC_LITERAL(69, 716, 12), // "noiseChanged"
QT_MOC_LITERAL(70, 729, 10), // "gainChange"
QT_MOC_LITERAL(71, 740, 5), // "value"
QT_MOC_LITERAL(72, 746, 12), // "offsetChange"
QT_MOC_LITERAL(73, 759, 15), // "resetGainOffset"
QT_MOC_LITERAL(74, 775, 13), // "fitGainOffset"
QT_MOC_LITERAL(75, 789, 15), // "changeImageMode"
QT_MOC_LITERAL(76, 805, 4), // "mode"
QT_MOC_LITERAL(77, 810, 7), // "snapPTC"
QT_MOC_LITERAL(78, 818, 8), // "resetPTC"
QT_MOC_LITERAL(79, 827, 7), // "savePTC"
QT_MOC_LITERAL(80, 835, 9), // "saveHPlot"
QT_MOC_LITERAL(81, 845, 9), // "saveVPlot"
QT_MOC_LITERAL(82, 855, 9), // "openFrame"
QT_MOC_LITERAL(83, 865, 8), // "filename"
QT_MOC_LITERAL(84, 874, 12), // "openHDRFrame"
QT_MOC_LITERAL(85, 887, 8), // "openFITS"
QT_MOC_LITERAL(86, 896, 9), // "saveFrame"
QT_MOC_LITERAL(87, 906, 8), // "saveFITS"
QT_MOC_LITERAL(88, 915, 12), // "saveSequence"
QT_MOC_LITERAL(89, 928, 14), // "rawZoomInClick"
QT_MOC_LITERAL(90, 943, 13), // "rawZoom1Click"
QT_MOC_LITERAL(91, 957, 15), // "rawZoomOutClick"
QT_MOC_LITERAL(92, 973, 15), // "rawImageMouseXY"
QT_MOC_LITERAL(93, 989, 14), // "rawPlotChanged"
QT_MOC_LITERAL(94, 1004, 14), // "rawStatChanged"
QT_MOC_LITERAL(95, 1019, 15), // "rawNoiseChanged"
QT_MOC_LITERAL(96, 1035, 13), // "rawGainChange"
QT_MOC_LITERAL(97, 1049, 15), // "rawOffsetChange"
QT_MOC_LITERAL(98, 1065, 18), // "resetRawGainOffset"
QT_MOC_LITERAL(99, 1084, 12), // "saveRawHPlot"
QT_MOC_LITERAL(100, 1097, 12), // "saveRawVPlot"
QT_MOC_LITERAL(101, 1110, 12), // "saveRawFrame"
QT_MOC_LITERAL(102, 1123, 8) // "applyNet"

    },
    "TArchonGUI\0openFile\0\0saveFile\0"
    "openNiceFile\0saveNiceFile\0showAbout\0"
    "testButton\0applyAll\0applyCDS\0loadTiming\0"
    "loadParameters\0test\0resetTiming\0"
    "holdTiming\0releaseTiming\0fetchFrame\0"
    "frame\0newFrame\0powerOn\0powerOff\0pollOn\0"
    "pollOff\0applySystem\0connectClicked\0"
    "flashClicked\0verifyClicked\0rebootClicked\0"
    "warmbootClicked\0flashActiveConfigClicked\0"
    "eraseStoredConfigClicked\0flashModuleClicked\0"
    "verifyModuleClicked\0poll\0logMessage\0"
    "msg\0progressMessage\0newstep\0newtotal\0"
    "msgSystem\0RMap\0data\0msgStatus\0"
    "msgFrameStatus\0msgConnected\0connected\0"
    "stateChanged\0clockChanged\0stateUp\0"
    "stateDown\0stateAdd\0stateDelete\0"
    "stateDuplicate\0zoomInClick\0zoom1Click\0"
    "zoomOutClick\0zoomFitClick\0imageMouseXY\0"
    "x\0y\0sample\0plotChanged\0hplot\0vplot\0"
    "statChanged\0x1\0y1\0x2\0y2\0noiseChanged\0"
    "gainChange\0value\0offsetChange\0"
    "resetGainOffset\0fitGainOffset\0"
    "changeImageMode\0mode\0snapPTC\0resetPTC\0"
    "savePTC\0saveHPlot\0saveVPlot\0openFrame\0"
    "filename\0openHDRFrame\0openFITS\0saveFrame\0"
    "saveFITS\0saveSequence\0rawZoomInClick\0"
    "rawZoom1Click\0rawZoomOutClick\0"
    "rawImageMouseXY\0rawPlotChanged\0"
    "rawStatChanged\0rawNoiseChanged\0"
    "rawGainChange\0rawOffsetChange\0"
    "resetRawGainOffset\0saveRawHPlot\0"
    "saveRawVPlot\0saveRawFrame\0applyNet"
};
#undef QT_MOC_LITERAL

static const uint qt_meta_data_TArchonGUI[] = {

 // content:
       8,       // revision
       0,       // classname
       0,    0, // classinfo
      85,   14, // methods
       0,    0, // properties
       0,    0, // enums/sets
       0,    0, // constructors
       0,       // flags
       0,       // signalCount

 // slots: name, argc, parameters, tag, flags
       1,    0,  439,    2, 0x0a /* Public */,
       3,    0,  440,    2, 0x0a /* Public */,
       4,    0,  441,    2, 0x0a /* Public */,
       5,    0,  442,    2, 0x0a /* Public */,
       6,    0,  443,    2, 0x0a /* Public */,
       7,    0,  444,    2, 0x0a /* Public */,
       8,    0,  445,    2, 0x0a /* Public */,
       9,    0,  446,    2, 0x0a /* Public */,
      10,    0,  447,    2, 0x0a /* Public */,
      11,    0,  448,    2, 0x0a /* Public */,
      12,    0,  449,    2, 0x0a /* Public */,
      13,    0,  450,    2, 0x0a /* Public */,
      14,    0,  451,    2, 0x0a /* Public */,
      15,    0,  452,    2, 0x0a /* Public */,
      16,    1,  453,    2, 0x0a /* Public */,
      18,    0,  456,    2, 0x0a /* Public */,
      19,    0,  457,    2, 0x0a /* Public */,
      20,    0,  458,    2, 0x0a /* Public */,
      21,    0,  459,    2, 0x0a /* Public */,
      22,    0,  460,    2, 0x0a /* Public */,
      23,    0,  461,    2, 0x0a /* Public */,
      24,    0,  462,    2, 0x0a /* Public */,
      25,    0,  463,    2, 0x0a /* Public */,
      26,    0,  464,    2, 0x0a /* Public */,
      27,    0,  465,    2, 0x0a /* Public */,
      28,    0,  466,    2, 0x0a /* Public */,
      29,    0,  467,    2, 0x0a /* Public */,
      30,    0,  468,    2, 0x0a /* Public */,
      31,    0,  469,    2, 0x0a /* Public */,
      32,    0,  470,    2, 0x0a /* Public */,
      33,    0,  471,    2, 0x0a /* Public */,
      34,    1,  472,    2, 0x0a /* Public */,
      36,    3,  475,    2, 0x0a /* Public */,
      39,    1,  482,    2, 0x0a /* Public */,
      42,    1,  485,    2, 0x0a /* Public */,
      43,    1,  488,    2, 0x0a /* Public */,
      44,    1,  491,    2, 0x0a /* Public */,
      46,    0,  494,    2, 0x0a /* Public */,
      47,    0,  495,    2, 0x0a /* Public */,
      48,    0,  496,    2, 0x0a /* Public */,
      49,    0,  497,    2, 0x0a /* Public */,
      50,    0,  498,    2, 0x0a /* Public */,
      51,    0,  499,    2, 0x0a /* Public */,
      52,    0,  500,    2, 0x0a /* Public */,
      53,    0,  501,    2, 0x0a /* Public */,
      54,    0,  502,    2, 0x0a /* Public */,
      55,    0,  503,    2, 0x0a /* Public */,
      56,    0,  504,    2, 0x0a /* Public */,
      57,    3,  505,    2, 0x0a /* Public */,
      61,    2,  512,    2, 0x0a /* Public */,
      61,    0,  517,    2, 0x0a /* Public */,
      64,    4,  518,    2, 0x0a /* Public */,
      69,    4,  527,    2, 0x0a /* Public */,
      70,    1,  536,    2, 0x0a /* Public */,
      72,    1,  539,    2, 0x0a /* Public */,
      73,    0,  542,    2, 0x0a /* Public */,
      74,    0,  543,    2, 0x0a /* Public */,
      75,    1,  544,    2, 0x0a /* Public */,
      77,    0,  547,    2, 0x0a /* Public */,
      78,    0,  548,    2, 0x0a /* Public */,
      79,    0,  549,    2, 0x0a /* Public */,
      80,    0,  550,    2, 0x0a /* Public */,
      81,    0,  551,    2, 0x0a /* Public */,
      82,    0,  552,    2, 0x0a /* Public */,
      82,    1,  553,    2, 0x0a /* Public */,
      84,    0,  556,    2, 0x0a /* Public */,
      85,    0,  557,    2, 0x0a /* Public */,
      86,    0,  558,    2, 0x0a /* Public */,
      87,    0,  559,    2, 0x0a /* Public */,
      88,    0,  560,    2, 0x0a /* Public */,
      89,    0,  561,    2, 0x0a /* Public */,
      90,    0,  562,    2, 0x0a /* Public */,
      91,    0,  563,    2, 0x0a /* Public */,
      92,    3,  564,    2, 0x0a /* Public */,
      93,    2,  571,    2, 0x0a /* Public */,
      93,    0,  576,    2, 0x0a /* Public */,
      94,    4,  577,    2, 0x0a /* Public */,
      95,    4,  586,    2, 0x0a /* Public */,
      96,    1,  595,    2, 0x0a /* Public */,
      97,    1,  598,    2, 0x0a /* Public */,
      98,    0,  601,    2, 0x0a /* Public */,
      99,    0,  602,    2, 0x0a /* Public */,
     100,    0,  603,    2, 0x0a /* Public */,
     101,    0,  604,    2, 0x0a /* Public */,
     102,    0,  605,    2, 0x0a /* Public */,

 // slots: parameters
    QMetaType::Void,
    QMetaType::Void,
    QMetaType::Void,
    QMetaType::Void,
    QMetaType::Void,
    QMetaType::Void,
    QMetaType::Void,
    QMetaType::Void,
    QMetaType::Void,
    QMetaType::Void,
    QMetaType::Void,
    QMetaType::Void,
    QMetaType::Void,
    QMetaType::Void,
    QMetaType::Void, QMetaType::Int,   17,
    QMetaType::Void,
    QMetaType::Void,
    QMetaType::Void,
    QMetaType::Void,
    QMetaType::Void,
    QMetaType::Void,
    QMetaType::Void,
    QMetaType::Void,
    QMetaType::Void,
    QMetaType::Void,
    QMetaType::Void,
    QMetaType::Void,
    QMetaType::Void,
    QMetaType::Void,
    QMetaType::Void,
    QMetaType::Void,
    QMetaType::Void, QMetaType::QString,   35,
    QMetaType::Void, QMetaType::QString, QMetaType::Int, QMetaType::Int,   35,   37,   38,
    QMetaType::Void, 0x80000000 | 40,   41,
    QMetaType::Void, 0x80000000 | 40,   41,
    QMetaType::Void, 0x80000000 | 40,   41,
    QMetaType::Void, QMetaType::Bool,   45,
    QMetaType::Void,
    QMetaType::Void,
    QMetaType::Void,
    QMetaType::Void,
    QMetaType::Void,
    QMetaType::Void,
    QMetaType::Void,
    QMetaType::Void,
    QMetaType::Void,
    QMetaType::Void,
    QMetaType::Void,
    QMetaType::Void, QMetaType::Int, QMetaType::Int, QMetaType::UInt,   58,   59,   60,
    QMetaType::Void, QMetaType::Int, QMetaType::Int,   62,   63,
    QMetaType::Void,
    QMetaType::Void, QMetaType::Int, QMetaType::Int, QMetaType::Int, QMetaType::Int,   65,   66,   67,   68,
    QMetaType::Void, QMetaType::Int, QMetaType::Int, QMetaType::Int, QMetaType::Int,   65,   66,   67,   68,
    QMetaType::Void, QMetaType::Int,   71,
    QMetaType::Void, QMetaType::Int,   71,
    QMetaType::Void,
    QMetaType::Void,
    QMetaType::Void, QMetaType::Int,   76,
    QMetaType::Void,
    QMetaType::Void,
    QMetaType::Void,
    QMetaType::Void,
    QMetaType::Void,
    QMetaType::Void,
    QMetaType::Bool, QMetaType::QString,   83,
    QMetaType::Void,
    QMetaType::Void,
    QMetaType::Void,
    QMetaType::Void,
    QMetaType::Void,
    QMetaType::Void,
    QMetaType::Void,
    QMetaType::Void,
    QMetaType::Void, QMetaType::Int, QMetaType::Int, QMetaType::UInt,   58,   59,   60,
    QMetaType::Void, QMetaType::Int, QMetaType::Int,   62,   63,
    QMetaType::Void,
    QMetaType::Void, QMetaType::Int, QMetaType::Int, QMetaType::Int, QMetaType::Int,   65,   66,   67,   68,
    QMetaType::Void, QMetaType::Int, QMetaType::Int, QMetaType::Int, QMetaType::Int,   65,   66,   67,   68,
    QMetaType::Void, QMetaType::Int,   71,
    QMetaType::Void, QMetaType::Int,   71,
    QMetaType::Void,
    QMetaType::Void,
    QMetaType::Void,
    QMetaType::Void,
    QMetaType::Void,

       0        // eod
};

void TArchonGUI::qt_static_metacall(QObject *_o, QMetaObject::Call _c, int _id, void **_a)
{
    if (_c == QMetaObject::InvokeMetaMethod) {
        auto *_t = static_cast<TArchonGUI *>(_o);
        (void)_t;
        switch (_id) {
        case 0: _t->openFile(); break;
        case 1: _t->saveFile(); break;
        case 2: _t->openNiceFile(); break;
        case 3: _t->saveNiceFile(); break;
        case 4: _t->showAbout(); break;
        case 5: _t->testButton(); break;
        case 6: _t->applyAll(); break;
        case 7: _t->applyCDS(); break;
        case 8: _t->loadTiming(); break;
        case 9: _t->loadParameters(); break;
        case 10: _t->test(); break;
        case 11: _t->resetTiming(); break;
        case 12: _t->holdTiming(); break;
        case 13: _t->releaseTiming(); break;
        case 14: _t->fetchFrame((*reinterpret_cast< int(*)>(_a[1]))); break;
        case 15: _t->newFrame(); break;
        case 16: _t->powerOn(); break;
        case 17: _t->powerOff(); break;
        case 18: _t->pollOn(); break;
        case 19: _t->pollOff(); break;
        case 20: _t->applySystem(); break;
        case 21: _t->connectClicked(); break;
        case 22: _t->flashClicked(); break;
        case 23: _t->verifyClicked(); break;
        case 24: _t->rebootClicked(); break;
        case 25: _t->warmbootClicked(); break;
        case 26: _t->flashActiveConfigClicked(); break;
        case 27: _t->eraseStoredConfigClicked(); break;
        case 28: _t->flashModuleClicked(); break;
        case 29: _t->verifyModuleClicked(); break;
        case 30: _t->poll(); break;
        case 31: _t->logMessage((*reinterpret_cast< const QString(*)>(_a[1]))); break;
        case 32: _t->progressMessage((*reinterpret_cast< const QString(*)>(_a[1])),(*reinterpret_cast< int(*)>(_a[2])),(*reinterpret_cast< int(*)>(_a[3]))); break;
        case 33: _t->msgSystem((*reinterpret_cast< const RMap(*)>(_a[1]))); break;
        case 34: _t->msgStatus((*reinterpret_cast< const RMap(*)>(_a[1]))); break;
        case 35: _t->msgFrameStatus((*reinterpret_cast< const RMap(*)>(_a[1]))); break;
        case 36: _t->msgConnected((*reinterpret_cast< const bool(*)>(_a[1]))); break;
        case 37: _t->stateChanged(); break;
        case 38: _t->clockChanged(); break;
        case 39: _t->stateUp(); break;
        case 40: _t->stateDown(); break;
        case 41: _t->stateAdd(); break;
        case 42: _t->stateDelete(); break;
        case 43: _t->stateDuplicate(); break;
        case 44: _t->zoomInClick(); break;
        case 45: _t->zoom1Click(); break;
        case 46: _t->zoomOutClick(); break;
        case 47: _t->zoomFitClick(); break;
        case 48: _t->imageMouseXY((*reinterpret_cast< int(*)>(_a[1])),(*reinterpret_cast< int(*)>(_a[2])),(*reinterpret_cast< uint(*)>(_a[3]))); break;
        case 49: _t->plotChanged((*reinterpret_cast< int(*)>(_a[1])),(*reinterpret_cast< int(*)>(_a[2]))); break;
        case 50: _t->plotChanged(); break;
        case 51: _t->statChanged((*reinterpret_cast< int(*)>(_a[1])),(*reinterpret_cast< int(*)>(_a[2])),(*reinterpret_cast< int(*)>(_a[3])),(*reinterpret_cast< int(*)>(_a[4]))); break;
        case 52: _t->noiseChanged((*reinterpret_cast< int(*)>(_a[1])),(*reinterpret_cast< int(*)>(_a[2])),(*reinterpret_cast< int(*)>(_a[3])),(*reinterpret_cast< int(*)>(_a[4]))); break;
        case 53: _t->gainChange((*reinterpret_cast< int(*)>(_a[1]))); break;
        case 54: _t->offsetChange((*reinterpret_cast< int(*)>(_a[1]))); break;
        case 55: _t->resetGainOffset(); break;
        case 56: _t->fitGainOffset(); break;
        case 57: _t->changeImageMode((*reinterpret_cast< int(*)>(_a[1]))); break;
        case 58: _t->snapPTC(); break;
        case 59: _t->resetPTC(); break;
        case 60: _t->savePTC(); break;
        case 61: _t->saveHPlot(); break;
        case 62: _t->saveVPlot(); break;
        case 63: _t->openFrame(); break;
        case 64: { bool _r = _t->openFrame((*reinterpret_cast< QString(*)>(_a[1])));
            if (_a[0]) *reinterpret_cast< bool*>(_a[0]) = std::move(_r); }  break;
        case 65: _t->openHDRFrame(); break;
        case 66: _t->openFITS(); break;
        case 67: _t->saveFrame(); break;
        case 68: _t->saveFITS(); break;
        case 69: _t->saveSequence(); break;
        case 70: _t->rawZoomInClick(); break;
        case 71: _t->rawZoom1Click(); break;
        case 72: _t->rawZoomOutClick(); break;
        case 73: _t->rawImageMouseXY((*reinterpret_cast< int(*)>(_a[1])),(*reinterpret_cast< int(*)>(_a[2])),(*reinterpret_cast< uint(*)>(_a[3]))); break;
        case 74: _t->rawPlotChanged((*reinterpret_cast< int(*)>(_a[1])),(*reinterpret_cast< int(*)>(_a[2]))); break;
        case 75: _t->rawPlotChanged(); break;
        case 76: _t->rawStatChanged((*reinterpret_cast< int(*)>(_a[1])),(*reinterpret_cast< int(*)>(_a[2])),(*reinterpret_cast< int(*)>(_a[3])),(*reinterpret_cast< int(*)>(_a[4]))); break;
        case 77: _t->rawNoiseChanged((*reinterpret_cast< int(*)>(_a[1])),(*reinterpret_cast< int(*)>(_a[2])),(*reinterpret_cast< int(*)>(_a[3])),(*reinterpret_cast< int(*)>(_a[4]))); break;
        case 78: _t->rawGainChange((*reinterpret_cast< int(*)>(_a[1]))); break;
        case 79: _t->rawOffsetChange((*reinterpret_cast< int(*)>(_a[1]))); break;
        case 80: _t->resetRawGainOffset(); break;
        case 81: _t->saveRawHPlot(); break;
        case 82: _t->saveRawVPlot(); break;
        case 83: _t->saveRawFrame(); break;
        case 84: _t->applyNet(); break;
        default: ;
        }
    }
}

QT_INIT_METAOBJECT const QMetaObject TArchonGUI::staticMetaObject = { {
    QMetaObject::SuperData::link<QMainWindow::staticMetaObject>(),
    qt_meta_stringdata_TArchonGUI.data,
    qt_meta_data_TArchonGUI,
    qt_static_metacall,
    nullptr,
    nullptr
} };


const QMetaObject *TArchonGUI::metaObject() const
{
    return QObject::d_ptr->metaObject ? QObject::d_ptr->dynamicMetaObject() : &staticMetaObject;
}

void *TArchonGUI::qt_metacast(const char *_clname)
{
    if (!_clname) return nullptr;
    if (!strcmp(_clname, qt_meta_stringdata_TArchonGUI.stringdata0))
        return static_cast<void*>(this);
    return QMainWindow::qt_metacast(_clname);
}

int TArchonGUI::qt_metacall(QMetaObject::Call _c, int _id, void **_a)
{
    _id = QMainWindow::qt_metacall(_c, _id, _a);
    if (_id < 0)
        return _id;
    if (_c == QMetaObject::InvokeMetaMethod) {
        if (_id < 85)
            qt_static_metacall(this, _c, _id, _a);
        _id -= 85;
    } else if (_c == QMetaObject::RegisterMethodArgumentMetaType) {
        if (_id < 85)
            *reinterpret_cast<int*>(_a[0]) = -1;
        _id -= 85;
    }
    return _id;
}
QT_WARNING_POP
QT_END_MOC_NAMESPACE
