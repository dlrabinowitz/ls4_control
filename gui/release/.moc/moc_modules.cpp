/****************************************************************************
** Meta object code from reading C++ file 'modules.h'
**
** Created by: The Qt Meta Object Compiler version 67 (Qt 5.15.3)
**
** WARNING! All changes made in this file will be lost!
*****************************************************************************/

#include <memory>
#include "../../src/modules.h"
#include <QtCore/qbytearray.h>
#include <QtCore/qmetatype.h>
#if !defined(Q_MOC_OUTPUT_REVISION)
#error "The header file 'modules.h' doesn't include <QObject>."
#elif Q_MOC_OUTPUT_REVISION != 67
#error "This file was generated using the moc from 5.15.3. It"
#error "cannot be used with the include files from this version of Qt."
#error "(The moc has changed too much.)"
#endif

QT_BEGIN_MOC_NAMESPACE
QT_WARNING_PUSH
QT_WARNING_DISABLE_DEPRECATED
struct qt_meta_stringdata_TModule_t {
    QByteArrayData data[1];
    char stringdata0[8];
};
#define QT_MOC_LITERAL(idx, ofs, len) \
    Q_STATIC_BYTE_ARRAY_DATA_HEADER_INITIALIZER_WITH_OFFSET(len, \
    qptrdiff(offsetof(qt_meta_stringdata_TModule_t, stringdata0) + ofs \
        - idx * sizeof(QByteArrayData)) \
    )
static const qt_meta_stringdata_TModule_t qt_meta_stringdata_TModule = {
    {
QT_MOC_LITERAL(0, 0, 7) // "TModule"

    },
    "TModule"
};
#undef QT_MOC_LITERAL

static const uint qt_meta_data_TModule[] = {

 // content:
       8,       // revision
       0,       // classname
       0,    0, // classinfo
       0,    0, // methods
       0,    0, // properties
       0,    0, // enums/sets
       0,    0, // constructors
       0,       // flags
       0,       // signalCount

       0        // eod
};

void TModule::qt_static_metacall(QObject *_o, QMetaObject::Call _c, int _id, void **_a)
{
    (void)_o;
    (void)_id;
    (void)_c;
    (void)_a;
}

QT_INIT_METAOBJECT const QMetaObject TModule::staticMetaObject = { {
    QMetaObject::SuperData::link<QObject::staticMetaObject>(),
    qt_meta_stringdata_TModule.data,
    qt_meta_data_TModule,
    qt_static_metacall,
    nullptr,
    nullptr
} };


const QMetaObject *TModule::metaObject() const
{
    return QObject::d_ptr->metaObject ? QObject::d_ptr->dynamicMetaObject() : &staticMetaObject;
}

void *TModule::qt_metacast(const char *_clname)
{
    if (!_clname) return nullptr;
    if (!strcmp(_clname, qt_meta_stringdata_TModule.stringdata0))
        return static_cast<void*>(this);
    return QObject::qt_metacast(_clname);
}

int TModule::qt_metacall(QMetaObject::Call _c, int _id, void **_a)
{
    _id = QObject::qt_metacall(_c, _id, _a);
    return _id;
}
struct qt_meta_stringdata_DRIVER_t {
    QByteArrayData data[6];
    char stringdata0[50];
};
#define QT_MOC_LITERAL(idx, ofs, len) \
    Q_STATIC_BYTE_ARRAY_DATA_HEADER_INITIALIZER_WITH_OFFSET(len, \
    qptrdiff(offsetof(qt_meta_stringdata_DRIVER_t, stringdata0) + ofs \
        - idx * sizeof(QByteArrayData)) \
    )
static const qt_meta_stringdata_DRIVER_t qt_meta_stringdata_DRIVER = {
    {
QT_MOC_LITERAL(0, 0, 6), // "DRIVER"
QT_MOC_LITERAL(1, 7, 12), // "clockChanged"
QT_MOC_LITERAL(2, 20, 0), // ""
QT_MOC_LITERAL(3, 21, 10), // "copyClocks"
QT_MOC_LITERAL(4, 32, 11), // "pasteClocks"
QT_MOC_LITERAL(5, 44, 5) // "apply"

    },
    "DRIVER\0clockChanged\0\0copyClocks\0"
    "pasteClocks\0apply"
};
#undef QT_MOC_LITERAL

static const uint qt_meta_data_DRIVER[] = {

 // content:
       8,       // revision
       0,       // classname
       0,    0, // classinfo
       4,   14, // methods
       0,    0, // properties
       0,    0, // enums/sets
       0,    0, // constructors
       0,       // flags
       0,       // signalCount

 // slots: name, argc, parameters, tag, flags
       1,    0,   34,    2, 0x0a /* Public */,
       3,    0,   35,    2, 0x0a /* Public */,
       4,    0,   36,    2, 0x0a /* Public */,
       5,    0,   37,    2, 0x0a /* Public */,

 // slots: parameters
    QMetaType::Void,
    QMetaType::Void,
    QMetaType::Void,
    QMetaType::Void,

       0        // eod
};

void DRIVER::qt_static_metacall(QObject *_o, QMetaObject::Call _c, int _id, void **_a)
{
    if (_c == QMetaObject::InvokeMetaMethod) {
        auto *_t = static_cast<DRIVER *>(_o);
        (void)_t;
        switch (_id) {
        case 0: _t->clockChanged(); break;
        case 1: _t->copyClocks(); break;
        case 2: _t->pasteClocks(); break;
        case 3: _t->apply(); break;
        default: ;
        }
    }
    (void)_a;
}

QT_INIT_METAOBJECT const QMetaObject DRIVER::staticMetaObject = { {
    QMetaObject::SuperData::link<TModule::staticMetaObject>(),
    qt_meta_stringdata_DRIVER.data,
    qt_meta_data_DRIVER,
    qt_static_metacall,
    nullptr,
    nullptr
} };


const QMetaObject *DRIVER::metaObject() const
{
    return QObject::d_ptr->metaObject ? QObject::d_ptr->dynamicMetaObject() : &staticMetaObject;
}

void *DRIVER::qt_metacast(const char *_clname)
{
    if (!_clname) return nullptr;
    if (!strcmp(_clname, qt_meta_stringdata_DRIVER.stringdata0))
        return static_cast<void*>(this);
    return TModule::qt_metacast(_clname);
}

int DRIVER::qt_metacall(QMetaObject::Call _c, int _id, void **_a)
{
    _id = TModule::qt_metacall(_c, _id, _a);
    if (_id < 0)
        return _id;
    if (_c == QMetaObject::InvokeMetaMethod) {
        if (_id < 4)
            qt_static_metacall(this, _c, _id, _a);
        _id -= 4;
    } else if (_c == QMetaObject::RegisterMethodArgumentMetaType) {
        if (_id < 4)
            *reinterpret_cast<int*>(_a[0]) = -1;
        _id -= 4;
    }
    return _id;
}
struct qt_meta_stringdata_DRIVERX_t {
    QByteArrayData data[6];
    char stringdata0[51];
};
#define QT_MOC_LITERAL(idx, ofs, len) \
    Q_STATIC_BYTE_ARRAY_DATA_HEADER_INITIALIZER_WITH_OFFSET(len, \
    qptrdiff(offsetof(qt_meta_stringdata_DRIVERX_t, stringdata0) + ofs \
        - idx * sizeof(QByteArrayData)) \
    )
static const qt_meta_stringdata_DRIVERX_t qt_meta_stringdata_DRIVERX = {
    {
QT_MOC_LITERAL(0, 0, 7), // "DRIVERX"
QT_MOC_LITERAL(1, 8, 12), // "clockChanged"
QT_MOC_LITERAL(2, 21, 0), // ""
QT_MOC_LITERAL(3, 22, 10), // "copyClocks"
QT_MOC_LITERAL(4, 33, 11), // "pasteClocks"
QT_MOC_LITERAL(5, 45, 5) // "apply"

    },
    "DRIVERX\0clockChanged\0\0copyClocks\0"
    "pasteClocks\0apply"
};
#undef QT_MOC_LITERAL

static const uint qt_meta_data_DRIVERX[] = {

 // content:
       8,       // revision
       0,       // classname
       0,    0, // classinfo
       4,   14, // methods
       0,    0, // properties
       0,    0, // enums/sets
       0,    0, // constructors
       0,       // flags
       0,       // signalCount

 // slots: name, argc, parameters, tag, flags
       1,    0,   34,    2, 0x0a /* Public */,
       3,    0,   35,    2, 0x0a /* Public */,
       4,    0,   36,    2, 0x0a /* Public */,
       5,    0,   37,    2, 0x0a /* Public */,

 // slots: parameters
    QMetaType::Void,
    QMetaType::Void,
    QMetaType::Void,
    QMetaType::Void,

       0        // eod
};

void DRIVERX::qt_static_metacall(QObject *_o, QMetaObject::Call _c, int _id, void **_a)
{
    if (_c == QMetaObject::InvokeMetaMethod) {
        auto *_t = static_cast<DRIVERX *>(_o);
        (void)_t;
        switch (_id) {
        case 0: _t->clockChanged(); break;
        case 1: _t->copyClocks(); break;
        case 2: _t->pasteClocks(); break;
        case 3: _t->apply(); break;
        default: ;
        }
    }
    (void)_a;
}

QT_INIT_METAOBJECT const QMetaObject DRIVERX::staticMetaObject = { {
    QMetaObject::SuperData::link<TModule::staticMetaObject>(),
    qt_meta_stringdata_DRIVERX.data,
    qt_meta_data_DRIVERX,
    qt_static_metacall,
    nullptr,
    nullptr
} };


const QMetaObject *DRIVERX::metaObject() const
{
    return QObject::d_ptr->metaObject ? QObject::d_ptr->dynamicMetaObject() : &staticMetaObject;
}

void *DRIVERX::qt_metacast(const char *_clname)
{
    if (!_clname) return nullptr;
    if (!strcmp(_clname, qt_meta_stringdata_DRIVERX.stringdata0))
        return static_cast<void*>(this);
    return TModule::qt_metacast(_clname);
}

int DRIVERX::qt_metacall(QMetaObject::Call _c, int _id, void **_a)
{
    _id = TModule::qt_metacall(_c, _id, _a);
    if (_id < 0)
        return _id;
    if (_c == QMetaObject::InvokeMetaMethod) {
        if (_id < 4)
            qt_static_metacall(this, _c, _id, _a);
        _id -= 4;
    } else if (_c == QMetaObject::RegisterMethodArgumentMetaType) {
        if (_id < 4)
            *reinterpret_cast<int*>(_a[0]) = -1;
        _id -= 4;
    }
    return _id;
}
struct qt_meta_stringdata_AD_t {
    QByteArrayData data[8];
    char stringdata0[62];
};
#define QT_MOC_LITERAL(idx, ofs, len) \
    Q_STATIC_BYTE_ARRAY_DATA_HEADER_INITIALIZER_WITH_OFFSET(len, \
    qptrdiff(offsetof(qt_meta_stringdata_AD_t, stringdata0) + ofs \
        - idx * sizeof(QByteArrayData)) \
    )
static const qt_meta_stringdata_AD_t qt_meta_stringdata_AD = {
    {
QT_MOC_LITERAL(0, 0, 2), // "AD"
QT_MOC_LITERAL(1, 3, 12), // "clockChanged"
QT_MOC_LITERAL(2, 16, 0), // ""
QT_MOC_LITERAL(3, 17, 10), // "copyClocks"
QT_MOC_LITERAL(4, 28, 11), // "pasteClocks"
QT_MOC_LITERAL(5, 40, 5), // "apply"
QT_MOC_LITERAL(6, 46, 8), // "clearCal"
QT_MOC_LITERAL(7, 55, 6) // "setCal"

    },
    "AD\0clockChanged\0\0copyClocks\0pasteClocks\0"
    "apply\0clearCal\0setCal"
};
#undef QT_MOC_LITERAL

static const uint qt_meta_data_AD[] = {

 // content:
       8,       // revision
       0,       // classname
       0,    0, // classinfo
       6,   14, // methods
       0,    0, // properties
       0,    0, // enums/sets
       0,    0, // constructors
       0,       // flags
       0,       // signalCount

 // slots: name, argc, parameters, tag, flags
       1,    0,   44,    2, 0x0a /* Public */,
       3,    0,   45,    2, 0x0a /* Public */,
       4,    0,   46,    2, 0x0a /* Public */,
       5,    0,   47,    2, 0x0a /* Public */,
       6,    0,   48,    2, 0x0a /* Public */,
       7,    0,   49,    2, 0x0a /* Public */,

 // slots: parameters
    QMetaType::Void,
    QMetaType::Void,
    QMetaType::Void,
    QMetaType::Void,
    QMetaType::Void,
    QMetaType::Void,

       0        // eod
};

void AD::qt_static_metacall(QObject *_o, QMetaObject::Call _c, int _id, void **_a)
{
    if (_c == QMetaObject::InvokeMetaMethod) {
        auto *_t = static_cast<AD *>(_o);
        (void)_t;
        switch (_id) {
        case 0: _t->clockChanged(); break;
        case 1: _t->copyClocks(); break;
        case 2: _t->pasteClocks(); break;
        case 3: _t->apply(); break;
        case 4: _t->clearCal(); break;
        case 5: _t->setCal(); break;
        default: ;
        }
    }
    (void)_a;
}

QT_INIT_METAOBJECT const QMetaObject AD::staticMetaObject = { {
    QMetaObject::SuperData::link<TModule::staticMetaObject>(),
    qt_meta_stringdata_AD.data,
    qt_meta_data_AD,
    qt_static_metacall,
    nullptr,
    nullptr
} };


const QMetaObject *AD::metaObject() const
{
    return QObject::d_ptr->metaObject ? QObject::d_ptr->dynamicMetaObject() : &staticMetaObject;
}

void *AD::qt_metacast(const char *_clname)
{
    if (!_clname) return nullptr;
    if (!strcmp(_clname, qt_meta_stringdata_AD.stringdata0))
        return static_cast<void*>(this);
    return TModule::qt_metacast(_clname);
}

int AD::qt_metacall(QMetaObject::Call _c, int _id, void **_a)
{
    _id = TModule::qt_metacall(_c, _id, _a);
    if (_id < 0)
        return _id;
    if (_c == QMetaObject::InvokeMetaMethod) {
        if (_id < 6)
            qt_static_metacall(this, _c, _id, _a);
        _id -= 6;
    } else if (_c == QMetaObject::RegisterMethodArgumentMetaType) {
        if (_id < 6)
            *reinterpret_cast<int*>(_a[0]) = -1;
        _id -= 6;
    }
    return _id;
}
struct qt_meta_stringdata_ADF_t {
    QByteArrayData data[8];
    char stringdata0[63];
};
#define QT_MOC_LITERAL(idx, ofs, len) \
    Q_STATIC_BYTE_ARRAY_DATA_HEADER_INITIALIZER_WITH_OFFSET(len, \
    qptrdiff(offsetof(qt_meta_stringdata_ADF_t, stringdata0) + ofs \
        - idx * sizeof(QByteArrayData)) \
    )
static const qt_meta_stringdata_ADF_t qt_meta_stringdata_ADF = {
    {
QT_MOC_LITERAL(0, 0, 3), // "ADF"
QT_MOC_LITERAL(1, 4, 12), // "clockChanged"
QT_MOC_LITERAL(2, 17, 0), // ""
QT_MOC_LITERAL(3, 18, 10), // "copyClocks"
QT_MOC_LITERAL(4, 29, 11), // "pasteClocks"
QT_MOC_LITERAL(5, 41, 5), // "apply"
QT_MOC_LITERAL(6, 47, 8), // "clearCal"
QT_MOC_LITERAL(7, 56, 6) // "setCal"

    },
    "ADF\0clockChanged\0\0copyClocks\0pasteClocks\0"
    "apply\0clearCal\0setCal"
};
#undef QT_MOC_LITERAL

static const uint qt_meta_data_ADF[] = {

 // content:
       8,       // revision
       0,       // classname
       0,    0, // classinfo
       6,   14, // methods
       0,    0, // properties
       0,    0, // enums/sets
       0,    0, // constructors
       0,       // flags
       0,       // signalCount

 // slots: name, argc, parameters, tag, flags
       1,    0,   44,    2, 0x0a /* Public */,
       3,    0,   45,    2, 0x0a /* Public */,
       4,    0,   46,    2, 0x0a /* Public */,
       5,    0,   47,    2, 0x0a /* Public */,
       6,    0,   48,    2, 0x0a /* Public */,
       7,    0,   49,    2, 0x0a /* Public */,

 // slots: parameters
    QMetaType::Void,
    QMetaType::Void,
    QMetaType::Void,
    QMetaType::Void,
    QMetaType::Void,
    QMetaType::Void,

       0        // eod
};

void ADF::qt_static_metacall(QObject *_o, QMetaObject::Call _c, int _id, void **_a)
{
    if (_c == QMetaObject::InvokeMetaMethod) {
        auto *_t = static_cast<ADF *>(_o);
        (void)_t;
        switch (_id) {
        case 0: _t->clockChanged(); break;
        case 1: _t->copyClocks(); break;
        case 2: _t->pasteClocks(); break;
        case 3: _t->apply(); break;
        case 4: _t->clearCal(); break;
        case 5: _t->setCal(); break;
        default: ;
        }
    }
    (void)_a;
}

QT_INIT_METAOBJECT const QMetaObject ADF::staticMetaObject = { {
    QMetaObject::SuperData::link<TModule::staticMetaObject>(),
    qt_meta_stringdata_ADF.data,
    qt_meta_data_ADF,
    qt_static_metacall,
    nullptr,
    nullptr
} };


const QMetaObject *ADF::metaObject() const
{
    return QObject::d_ptr->metaObject ? QObject::d_ptr->dynamicMetaObject() : &staticMetaObject;
}

void *ADF::qt_metacast(const char *_clname)
{
    if (!_clname) return nullptr;
    if (!strcmp(_clname, qt_meta_stringdata_ADF.stringdata0))
        return static_cast<void*>(this);
    return TModule::qt_metacast(_clname);
}

int ADF::qt_metacall(QMetaObject::Call _c, int _id, void **_a)
{
    _id = TModule::qt_metacall(_c, _id, _a);
    if (_id < 0)
        return _id;
    if (_c == QMetaObject::InvokeMetaMethod) {
        if (_id < 6)
            qt_static_metacall(this, _c, _id, _a);
        _id -= 6;
    } else if (_c == QMetaObject::RegisterMethodArgumentMetaType) {
        if (_id < 6)
            *reinterpret_cast<int*>(_a[0]) = -1;
        _id -= 6;
    }
    return _id;
}
struct qt_meta_stringdata_ADX_t {
    QByteArrayData data[6];
    char stringdata0[47];
};
#define QT_MOC_LITERAL(idx, ofs, len) \
    Q_STATIC_BYTE_ARRAY_DATA_HEADER_INITIALIZER_WITH_OFFSET(len, \
    qptrdiff(offsetof(qt_meta_stringdata_ADX_t, stringdata0) + ofs \
        - idx * sizeof(QByteArrayData)) \
    )
static const qt_meta_stringdata_ADX_t qt_meta_stringdata_ADX = {
    {
QT_MOC_LITERAL(0, 0, 3), // "ADX"
QT_MOC_LITERAL(1, 4, 12), // "clockChanged"
QT_MOC_LITERAL(2, 17, 0), // ""
QT_MOC_LITERAL(3, 18, 10), // "copyClocks"
QT_MOC_LITERAL(4, 29, 11), // "pasteClocks"
QT_MOC_LITERAL(5, 41, 5) // "apply"

    },
    "ADX\0clockChanged\0\0copyClocks\0pasteClocks\0"
    "apply"
};
#undef QT_MOC_LITERAL

static const uint qt_meta_data_ADX[] = {

 // content:
       8,       // revision
       0,       // classname
       0,    0, // classinfo
       4,   14, // methods
       0,    0, // properties
       0,    0, // enums/sets
       0,    0, // constructors
       0,       // flags
       0,       // signalCount

 // slots: name, argc, parameters, tag, flags
       1,    0,   34,    2, 0x0a /* Public */,
       3,    0,   35,    2, 0x0a /* Public */,
       4,    0,   36,    2, 0x0a /* Public */,
       5,    0,   37,    2, 0x0a /* Public */,

 // slots: parameters
    QMetaType::Void,
    QMetaType::Void,
    QMetaType::Void,
    QMetaType::Void,

       0        // eod
};

void ADX::qt_static_metacall(QObject *_o, QMetaObject::Call _c, int _id, void **_a)
{
    if (_c == QMetaObject::InvokeMetaMethod) {
        auto *_t = static_cast<ADX *>(_o);
        (void)_t;
        switch (_id) {
        case 0: _t->clockChanged(); break;
        case 1: _t->copyClocks(); break;
        case 2: _t->pasteClocks(); break;
        case 3: _t->apply(); break;
        default: ;
        }
    }
    (void)_a;
}

QT_INIT_METAOBJECT const QMetaObject ADX::staticMetaObject = { {
    QMetaObject::SuperData::link<TModule::staticMetaObject>(),
    qt_meta_stringdata_ADX.data,
    qt_meta_data_ADX,
    qt_static_metacall,
    nullptr,
    nullptr
} };


const QMetaObject *ADX::metaObject() const
{
    return QObject::d_ptr->metaObject ? QObject::d_ptr->dynamicMetaObject() : &staticMetaObject;
}

void *ADX::qt_metacast(const char *_clname)
{
    if (!_clname) return nullptr;
    if (!strcmp(_clname, qt_meta_stringdata_ADX.stringdata0))
        return static_cast<void*>(this);
    return TModule::qt_metacast(_clname);
}

int ADX::qt_metacall(QMetaObject::Call _c, int _id, void **_a)
{
    _id = TModule::qt_metacall(_c, _id, _a);
    if (_id < 0)
        return _id;
    if (_c == QMetaObject::InvokeMetaMethod) {
        if (_id < 4)
            qt_static_metacall(this, _c, _id, _a);
        _id -= 4;
    } else if (_c == QMetaObject::RegisterMethodArgumentMetaType) {
        if (_id < 4)
            *reinterpret_cast<int*>(_a[0]) = -1;
        _id -= 4;
    }
    return _id;
}
struct qt_meta_stringdata_ADLN_t {
    QByteArrayData data[8];
    char stringdata0[64];
};
#define QT_MOC_LITERAL(idx, ofs, len) \
    Q_STATIC_BYTE_ARRAY_DATA_HEADER_INITIALIZER_WITH_OFFSET(len, \
    qptrdiff(offsetof(qt_meta_stringdata_ADLN_t, stringdata0) + ofs \
        - idx * sizeof(QByteArrayData)) \
    )
static const qt_meta_stringdata_ADLN_t qt_meta_stringdata_ADLN = {
    {
QT_MOC_LITERAL(0, 0, 4), // "ADLN"
QT_MOC_LITERAL(1, 5, 12), // "clockChanged"
QT_MOC_LITERAL(2, 18, 0), // ""
QT_MOC_LITERAL(3, 19, 10), // "copyClocks"
QT_MOC_LITERAL(4, 30, 11), // "pasteClocks"
QT_MOC_LITERAL(5, 42, 5), // "apply"
QT_MOC_LITERAL(6, 48, 8), // "clearCal"
QT_MOC_LITERAL(7, 57, 6) // "setCal"

    },
    "ADLN\0clockChanged\0\0copyClocks\0pasteClocks\0"
    "apply\0clearCal\0setCal"
};
#undef QT_MOC_LITERAL

static const uint qt_meta_data_ADLN[] = {

 // content:
       8,       // revision
       0,       // classname
       0,    0, // classinfo
       6,   14, // methods
       0,    0, // properties
       0,    0, // enums/sets
       0,    0, // constructors
       0,       // flags
       0,       // signalCount

 // slots: name, argc, parameters, tag, flags
       1,    0,   44,    2, 0x0a /* Public */,
       3,    0,   45,    2, 0x0a /* Public */,
       4,    0,   46,    2, 0x0a /* Public */,
       5,    0,   47,    2, 0x0a /* Public */,
       6,    0,   48,    2, 0x0a /* Public */,
       7,    0,   49,    2, 0x0a /* Public */,

 // slots: parameters
    QMetaType::Void,
    QMetaType::Void,
    QMetaType::Void,
    QMetaType::Void,
    QMetaType::Void,
    QMetaType::Void,

       0        // eod
};

void ADLN::qt_static_metacall(QObject *_o, QMetaObject::Call _c, int _id, void **_a)
{
    if (_c == QMetaObject::InvokeMetaMethod) {
        auto *_t = static_cast<ADLN *>(_o);
        (void)_t;
        switch (_id) {
        case 0: _t->clockChanged(); break;
        case 1: _t->copyClocks(); break;
        case 2: _t->pasteClocks(); break;
        case 3: _t->apply(); break;
        case 4: _t->clearCal(); break;
        case 5: _t->setCal(); break;
        default: ;
        }
    }
    (void)_a;
}

QT_INIT_METAOBJECT const QMetaObject ADLN::staticMetaObject = { {
    QMetaObject::SuperData::link<TModule::staticMetaObject>(),
    qt_meta_stringdata_ADLN.data,
    qt_meta_data_ADLN,
    qt_static_metacall,
    nullptr,
    nullptr
} };


const QMetaObject *ADLN::metaObject() const
{
    return QObject::d_ptr->metaObject ? QObject::d_ptr->dynamicMetaObject() : &staticMetaObject;
}

void *ADLN::qt_metacast(const char *_clname)
{
    if (!_clname) return nullptr;
    if (!strcmp(_clname, qt_meta_stringdata_ADLN.stringdata0))
        return static_cast<void*>(this);
    return TModule::qt_metacast(_clname);
}

int ADLN::qt_metacall(QMetaObject::Call _c, int _id, void **_a)
{
    _id = TModule::qt_metacall(_c, _id, _a);
    if (_id < 0)
        return _id;
    if (_c == QMetaObject::InvokeMetaMethod) {
        if (_id < 6)
            qt_static_metacall(this, _c, _id, _a);
        _id -= 6;
    } else if (_c == QMetaObject::RegisterMethodArgumentMetaType) {
        if (_id < 6)
            *reinterpret_cast<int*>(_a[0]) = -1;
        _id -= 6;
    }
    return _id;
}
struct qt_meta_stringdata_ADM_t {
    QByteArrayData data[5];
    char stringdata0[41];
};
#define QT_MOC_LITERAL(idx, ofs, len) \
    Q_STATIC_BYTE_ARRAY_DATA_HEADER_INITIALIZER_WITH_OFFSET(len, \
    qptrdiff(offsetof(qt_meta_stringdata_ADM_t, stringdata0) + ofs \
        - idx * sizeof(QByteArrayData)) \
    )
static const qt_meta_stringdata_ADM_t qt_meta_stringdata_ADM = {
    {
QT_MOC_LITERAL(0, 0, 3), // "ADM"
QT_MOC_LITERAL(1, 4, 12), // "clockChanged"
QT_MOC_LITERAL(2, 17, 0), // ""
QT_MOC_LITERAL(3, 18, 10), // "copyClocks"
QT_MOC_LITERAL(4, 29, 11) // "pasteClocks"

    },
    "ADM\0clockChanged\0\0copyClocks\0pasteClocks"
};
#undef QT_MOC_LITERAL

static const uint qt_meta_data_ADM[] = {

 // content:
       8,       // revision
       0,       // classname
       0,    0, // classinfo
       3,   14, // methods
       0,    0, // properties
       0,    0, // enums/sets
       0,    0, // constructors
       0,       // flags
       0,       // signalCount

 // slots: name, argc, parameters, tag, flags
       1,    0,   29,    2, 0x0a /* Public */,
       3,    0,   30,    2, 0x0a /* Public */,
       4,    0,   31,    2, 0x0a /* Public */,

 // slots: parameters
    QMetaType::Void,
    QMetaType::Void,
    QMetaType::Void,

       0        // eod
};

void ADM::qt_static_metacall(QObject *_o, QMetaObject::Call _c, int _id, void **_a)
{
    if (_c == QMetaObject::InvokeMetaMethod) {
        auto *_t = static_cast<ADM *>(_o);
        (void)_t;
        switch (_id) {
        case 0: _t->clockChanged(); break;
        case 1: _t->copyClocks(); break;
        case 2: _t->pasteClocks(); break;
        default: ;
        }
    }
    (void)_a;
}

QT_INIT_METAOBJECT const QMetaObject ADM::staticMetaObject = { {
    QMetaObject::SuperData::link<TModule::staticMetaObject>(),
    qt_meta_stringdata_ADM.data,
    qt_meta_data_ADM,
    qt_static_metacall,
    nullptr,
    nullptr
} };


const QMetaObject *ADM::metaObject() const
{
    return QObject::d_ptr->metaObject ? QObject::d_ptr->dynamicMetaObject() : &staticMetaObject;
}

void *ADM::qt_metacast(const char *_clname)
{
    if (!_clname) return nullptr;
    if (!strcmp(_clname, qt_meta_stringdata_ADM.stringdata0))
        return static_cast<void*>(this);
    return TModule::qt_metacast(_clname);
}

int ADM::qt_metacall(QMetaObject::Call _c, int _id, void **_a)
{
    _id = TModule::qt_metacall(_c, _id, _a);
    if (_id < 0)
        return _id;
    if (_c == QMetaObject::InvokeMetaMethod) {
        if (_id < 3)
            qt_static_metacall(this, _c, _id, _a);
        _id -= 3;
    } else if (_c == QMetaObject::RegisterMethodArgumentMetaType) {
        if (_id < 3)
            *reinterpret_cast<int*>(_a[0]) = -1;
        _id -= 3;
    }
    return _id;
}
struct qt_meta_stringdata_LVBIAS_t {
    QByteArrayData data[7];
    char stringdata0[59];
};
#define QT_MOC_LITERAL(idx, ofs, len) \
    Q_STATIC_BYTE_ARRAY_DATA_HEADER_INITIALIZER_WITH_OFFSET(len, \
    qptrdiff(offsetof(qt_meta_stringdata_LVBIAS_t, stringdata0) + ofs \
        - idx * sizeof(QByteArrayData)) \
    )
static const qt_meta_stringdata_LVBIAS_t qt_meta_stringdata_LVBIAS = {
    {
QT_MOC_LITERAL(0, 0, 6), // "LVBIAS"
QT_MOC_LITERAL(1, 7, 12), // "clockChanged"
QT_MOC_LITERAL(2, 20, 0), // ""
QT_MOC_LITERAL(3, 21, 10), // "copyClocks"
QT_MOC_LITERAL(4, 32, 11), // "pasteClocks"
QT_MOC_LITERAL(5, 44, 5), // "apply"
QT_MOC_LITERAL(6, 50, 8) // "applyDIO"

    },
    "LVBIAS\0clockChanged\0\0copyClocks\0"
    "pasteClocks\0apply\0applyDIO"
};
#undef QT_MOC_LITERAL

static const uint qt_meta_data_LVBIAS[] = {

 // content:
       8,       // revision
       0,       // classname
       0,    0, // classinfo
       5,   14, // methods
       0,    0, // properties
       0,    0, // enums/sets
       0,    0, // constructors
       0,       // flags
       0,       // signalCount

 // slots: name, argc, parameters, tag, flags
       1,    0,   39,    2, 0x0a /* Public */,
       3,    0,   40,    2, 0x0a /* Public */,
       4,    0,   41,    2, 0x0a /* Public */,
       5,    0,   42,    2, 0x0a /* Public */,
       6,    0,   43,    2, 0x0a /* Public */,

 // slots: parameters
    QMetaType::Void,
    QMetaType::Void,
    QMetaType::Void,
    QMetaType::Void,
    QMetaType::Void,

       0        // eod
};

void LVBIAS::qt_static_metacall(QObject *_o, QMetaObject::Call _c, int _id, void **_a)
{
    if (_c == QMetaObject::InvokeMetaMethod) {
        auto *_t = static_cast<LVBIAS *>(_o);
        (void)_t;
        switch (_id) {
        case 0: _t->clockChanged(); break;
        case 1: _t->copyClocks(); break;
        case 2: _t->pasteClocks(); break;
        case 3: _t->apply(); break;
        case 4: _t->applyDIO(); break;
        default: ;
        }
    }
    (void)_a;
}

QT_INIT_METAOBJECT const QMetaObject LVBIAS::staticMetaObject = { {
    QMetaObject::SuperData::link<TModule::staticMetaObject>(),
    qt_meta_stringdata_LVBIAS.data,
    qt_meta_data_LVBIAS,
    qt_static_metacall,
    nullptr,
    nullptr
} };


const QMetaObject *LVBIAS::metaObject() const
{
    return QObject::d_ptr->metaObject ? QObject::d_ptr->dynamicMetaObject() : &staticMetaObject;
}

void *LVBIAS::qt_metacast(const char *_clname)
{
    if (!_clname) return nullptr;
    if (!strcmp(_clname, qt_meta_stringdata_LVBIAS.stringdata0))
        return static_cast<void*>(this);
    return TModule::qt_metacast(_clname);
}

int LVBIAS::qt_metacall(QMetaObject::Call _c, int _id, void **_a)
{
    _id = TModule::qt_metacall(_c, _id, _a);
    if (_id < 0)
        return _id;
    if (_c == QMetaObject::InvokeMetaMethod) {
        if (_id < 5)
            qt_static_metacall(this, _c, _id, _a);
        _id -= 5;
    } else if (_c == QMetaObject::RegisterMethodArgumentMetaType) {
        if (_id < 5)
            *reinterpret_cast<int*>(_a[0]) = -1;
        _id -= 5;
    }
    return _id;
}
struct qt_meta_stringdata_HVBIAS_t {
    QByteArrayData data[6];
    char stringdata0[50];
};
#define QT_MOC_LITERAL(idx, ofs, len) \
    Q_STATIC_BYTE_ARRAY_DATA_HEADER_INITIALIZER_WITH_OFFSET(len, \
    qptrdiff(offsetof(qt_meta_stringdata_HVBIAS_t, stringdata0) + ofs \
        - idx * sizeof(QByteArrayData)) \
    )
static const qt_meta_stringdata_HVBIAS_t qt_meta_stringdata_HVBIAS = {
    {
QT_MOC_LITERAL(0, 0, 6), // "HVBIAS"
QT_MOC_LITERAL(1, 7, 12), // "clockChanged"
QT_MOC_LITERAL(2, 20, 0), // ""
QT_MOC_LITERAL(3, 21, 10), // "copyClocks"
QT_MOC_LITERAL(4, 32, 11), // "pasteClocks"
QT_MOC_LITERAL(5, 44, 5) // "apply"

    },
    "HVBIAS\0clockChanged\0\0copyClocks\0"
    "pasteClocks\0apply"
};
#undef QT_MOC_LITERAL

static const uint qt_meta_data_HVBIAS[] = {

 // content:
       8,       // revision
       0,       // classname
       0,    0, // classinfo
       4,   14, // methods
       0,    0, // properties
       0,    0, // enums/sets
       0,    0, // constructors
       0,       // flags
       0,       // signalCount

 // slots: name, argc, parameters, tag, flags
       1,    0,   34,    2, 0x0a /* Public */,
       3,    0,   35,    2, 0x0a /* Public */,
       4,    0,   36,    2, 0x0a /* Public */,
       5,    0,   37,    2, 0x0a /* Public */,

 // slots: parameters
    QMetaType::Void,
    QMetaType::Void,
    QMetaType::Void,
    QMetaType::Void,

       0        // eod
};

void HVBIAS::qt_static_metacall(QObject *_o, QMetaObject::Call _c, int _id, void **_a)
{
    if (_c == QMetaObject::InvokeMetaMethod) {
        auto *_t = static_cast<HVBIAS *>(_o);
        (void)_t;
        switch (_id) {
        case 0: _t->clockChanged(); break;
        case 1: _t->copyClocks(); break;
        case 2: _t->pasteClocks(); break;
        case 3: _t->apply(); break;
        default: ;
        }
    }
    (void)_a;
}

QT_INIT_METAOBJECT const QMetaObject HVBIAS::staticMetaObject = { {
    QMetaObject::SuperData::link<TModule::staticMetaObject>(),
    qt_meta_stringdata_HVBIAS.data,
    qt_meta_data_HVBIAS,
    qt_static_metacall,
    nullptr,
    nullptr
} };


const QMetaObject *HVBIAS::metaObject() const
{
    return QObject::d_ptr->metaObject ? QObject::d_ptr->dynamicMetaObject() : &staticMetaObject;
}

void *HVBIAS::qt_metacast(const char *_clname)
{
    if (!_clname) return nullptr;
    if (!strcmp(_clname, qt_meta_stringdata_HVBIAS.stringdata0))
        return static_cast<void*>(this);
    return TModule::qt_metacast(_clname);
}

int HVBIAS::qt_metacall(QMetaObject::Call _c, int _id, void **_a)
{
    _id = TModule::qt_metacall(_c, _id, _a);
    if (_id < 0)
        return _id;
    if (_c == QMetaObject::InvokeMetaMethod) {
        if (_id < 4)
            qt_static_metacall(this, _c, _id, _a);
        _id -= 4;
    } else if (_c == QMetaObject::RegisterMethodArgumentMetaType) {
        if (_id < 4)
            *reinterpret_cast<int*>(_a[0]) = -1;
        _id -= 4;
    }
    return _id;
}
struct qt_meta_stringdata_HEATER_t {
    QByteArrayData data[10];
    char stringdata0[100];
};
#define QT_MOC_LITERAL(idx, ofs, len) \
    Q_STATIC_BYTE_ARRAY_DATA_HEADER_INITIALIZER_WITH_OFFSET(len, \
    qptrdiff(offsetof(qt_meta_stringdata_HEATER_t, stringdata0) + ofs \
        - idx * sizeof(QByteArrayData)) \
    )
static const qt_meta_stringdata_HEATER_t qt_meta_stringdata_HEATER = {
    {
QT_MOC_LITERAL(0, 0, 6), // "HEATER"
QT_MOC_LITERAL(1, 7, 12), // "clockChanged"
QT_MOC_LITERAL(2, 20, 0), // ""
QT_MOC_LITERAL(3, 21, 10), // "copyClocks"
QT_MOC_LITERAL(4, 32, 11), // "pasteClocks"
QT_MOC_LITERAL(5, 44, 5), // "apply"
QT_MOC_LITERAL(6, 50, 8), // "applyDIO"
QT_MOC_LITERAL(7, 59, 14), // "enablePlotting"
QT_MOC_LITERAL(8, 74, 15), // "disablePlotting"
QT_MOC_LITERAL(9, 90, 9) // "savePlots"

    },
    "HEATER\0clockChanged\0\0copyClocks\0"
    "pasteClocks\0apply\0applyDIO\0enablePlotting\0"
    "disablePlotting\0savePlots"
};
#undef QT_MOC_LITERAL

static const uint qt_meta_data_HEATER[] = {

 // content:
       8,       // revision
       0,       // classname
       0,    0, // classinfo
       8,   14, // methods
       0,    0, // properties
       0,    0, // enums/sets
       0,    0, // constructors
       0,       // flags
       0,       // signalCount

 // slots: name, argc, parameters, tag, flags
       1,    0,   54,    2, 0x0a /* Public */,
       3,    0,   55,    2, 0x0a /* Public */,
       4,    0,   56,    2, 0x0a /* Public */,
       5,    0,   57,    2, 0x0a /* Public */,
       6,    0,   58,    2, 0x0a /* Public */,
       7,    0,   59,    2, 0x0a /* Public */,
       8,    0,   60,    2, 0x0a /* Public */,
       9,    0,   61,    2, 0x0a /* Public */,

 // slots: parameters
    QMetaType::Void,
    QMetaType::Void,
    QMetaType::Void,
    QMetaType::Void,
    QMetaType::Void,
    QMetaType::Void,
    QMetaType::Void,
    QMetaType::Void,

       0        // eod
};

void HEATER::qt_static_metacall(QObject *_o, QMetaObject::Call _c, int _id, void **_a)
{
    if (_c == QMetaObject::InvokeMetaMethod) {
        auto *_t = static_cast<HEATER *>(_o);
        (void)_t;
        switch (_id) {
        case 0: _t->clockChanged(); break;
        case 1: _t->copyClocks(); break;
        case 2: _t->pasteClocks(); break;
        case 3: _t->apply(); break;
        case 4: _t->applyDIO(); break;
        case 5: _t->enablePlotting(); break;
        case 6: _t->disablePlotting(); break;
        case 7: _t->savePlots(); break;
        default: ;
        }
    }
    (void)_a;
}

QT_INIT_METAOBJECT const QMetaObject HEATER::staticMetaObject = { {
    QMetaObject::SuperData::link<TModule::staticMetaObject>(),
    qt_meta_stringdata_HEATER.data,
    qt_meta_data_HEATER,
    qt_static_metacall,
    nullptr,
    nullptr
} };


const QMetaObject *HEATER::metaObject() const
{
    return QObject::d_ptr->metaObject ? QObject::d_ptr->dynamicMetaObject() : &staticMetaObject;
}

void *HEATER::qt_metacast(const char *_clname)
{
    if (!_clname) return nullptr;
    if (!strcmp(_clname, qt_meta_stringdata_HEATER.stringdata0))
        return static_cast<void*>(this);
    return TModule::qt_metacast(_clname);
}

int HEATER::qt_metacall(QMetaObject::Call _c, int _id, void **_a)
{
    _id = TModule::qt_metacall(_c, _id, _a);
    if (_id < 0)
        return _id;
    if (_c == QMetaObject::InvokeMetaMethod) {
        if (_id < 8)
            qt_static_metacall(this, _c, _id, _a);
        _id -= 8;
    } else if (_c == QMetaObject::RegisterMethodArgumentMetaType) {
        if (_id < 8)
            *reinterpret_cast<int*>(_a[0]) = -1;
        _id -= 8;
    }
    return _id;
}
struct qt_meta_stringdata_ATLAS_t {
    QByteArrayData data[9];
    char stringdata0[82];
};
#define QT_MOC_LITERAL(idx, ofs, len) \
    Q_STATIC_BYTE_ARRAY_DATA_HEADER_INITIALIZER_WITH_OFFSET(len, \
    qptrdiff(offsetof(qt_meta_stringdata_ATLAS_t, stringdata0) + ofs \
        - idx * sizeof(QByteArrayData)) \
    )
static const qt_meta_stringdata_ATLAS_t qt_meta_stringdata_ATLAS = {
    {
QT_MOC_LITERAL(0, 0, 5), // "ATLAS"
QT_MOC_LITERAL(1, 6, 12), // "clockChanged"
QT_MOC_LITERAL(2, 19, 0), // ""
QT_MOC_LITERAL(3, 20, 10), // "copyClocks"
QT_MOC_LITERAL(4, 31, 11), // "pasteClocks"
QT_MOC_LITERAL(5, 43, 5), // "apply"
QT_MOC_LITERAL(6, 49, 10), // "moveMotor1"
QT_MOC_LITERAL(7, 60, 10), // "moveMotor2"
QT_MOC_LITERAL(8, 71, 10) // "moveMotor3"

    },
    "ATLAS\0clockChanged\0\0copyClocks\0"
    "pasteClocks\0apply\0moveMotor1\0moveMotor2\0"
    "moveMotor3"
};
#undef QT_MOC_LITERAL

static const uint qt_meta_data_ATLAS[] = {

 // content:
       8,       // revision
       0,       // classname
       0,    0, // classinfo
       7,   14, // methods
       0,    0, // properties
       0,    0, // enums/sets
       0,    0, // constructors
       0,       // flags
       0,       // signalCount

 // slots: name, argc, parameters, tag, flags
       1,    0,   49,    2, 0x0a /* Public */,
       3,    0,   50,    2, 0x0a /* Public */,
       4,    0,   51,    2, 0x0a /* Public */,
       5,    0,   52,    2, 0x0a /* Public */,
       6,    0,   53,    2, 0x0a /* Public */,
       7,    0,   54,    2, 0x0a /* Public */,
       8,    0,   55,    2, 0x0a /* Public */,

 // slots: parameters
    QMetaType::Void,
    QMetaType::Void,
    QMetaType::Void,
    QMetaType::Void,
    QMetaType::Void,
    QMetaType::Void,
    QMetaType::Void,

       0        // eod
};

void ATLAS::qt_static_metacall(QObject *_o, QMetaObject::Call _c, int _id, void **_a)
{
    if (_c == QMetaObject::InvokeMetaMethod) {
        auto *_t = static_cast<ATLAS *>(_o);
        (void)_t;
        switch (_id) {
        case 0: _t->clockChanged(); break;
        case 1: _t->copyClocks(); break;
        case 2: _t->pasteClocks(); break;
        case 3: _t->apply(); break;
        case 4: _t->moveMotor1(); break;
        case 5: _t->moveMotor2(); break;
        case 6: _t->moveMotor3(); break;
        default: ;
        }
    }
    (void)_a;
}

QT_INIT_METAOBJECT const QMetaObject ATLAS::staticMetaObject = { {
    QMetaObject::SuperData::link<TModule::staticMetaObject>(),
    qt_meta_stringdata_ATLAS.data,
    qt_meta_data_ATLAS,
    qt_static_metacall,
    nullptr,
    nullptr
} };


const QMetaObject *ATLAS::metaObject() const
{
    return QObject::d_ptr->metaObject ? QObject::d_ptr->dynamicMetaObject() : &staticMetaObject;
}

void *ATLAS::qt_metacast(const char *_clname)
{
    if (!_clname) return nullptr;
    if (!strcmp(_clname, qt_meta_stringdata_ATLAS.stringdata0))
        return static_cast<void*>(this);
    return TModule::qt_metacast(_clname);
}

int ATLAS::qt_metacall(QMetaObject::Call _c, int _id, void **_a)
{
    _id = TModule::qt_metacall(_c, _id, _a);
    if (_id < 0)
        return _id;
    if (_c == QMetaObject::InvokeMetaMethod) {
        if (_id < 7)
            qt_static_metacall(this, _c, _id, _a);
        _id -= 7;
    } else if (_c == QMetaObject::RegisterMethodArgumentMetaType) {
        if (_id < 7)
            *reinterpret_cast<int*>(_a[0]) = -1;
        _id -= 7;
    }
    return _id;
}
struct qt_meta_stringdata_HS_t {
    QByteArrayData data[7];
    char stringdata0[55];
};
#define QT_MOC_LITERAL(idx, ofs, len) \
    Q_STATIC_BYTE_ARRAY_DATA_HEADER_INITIALIZER_WITH_OFFSET(len, \
    qptrdiff(offsetof(qt_meta_stringdata_HS_t, stringdata0) + ofs \
        - idx * sizeof(QByteArrayData)) \
    )
static const qt_meta_stringdata_HS_t qt_meta_stringdata_HS = {
    {
QT_MOC_LITERAL(0, 0, 2), // "HS"
QT_MOC_LITERAL(1, 3, 12), // "clockChanged"
QT_MOC_LITERAL(2, 16, 0), // ""
QT_MOC_LITERAL(3, 17, 10), // "copyClocks"
QT_MOC_LITERAL(4, 28, 11), // "pasteClocks"
QT_MOC_LITERAL(5, 40, 5), // "apply"
QT_MOC_LITERAL(6, 46, 8) // "applyDIO"

    },
    "HS\0clockChanged\0\0copyClocks\0pasteClocks\0"
    "apply\0applyDIO"
};
#undef QT_MOC_LITERAL

static const uint qt_meta_data_HS[] = {

 // content:
       8,       // revision
       0,       // classname
       0,    0, // classinfo
       5,   14, // methods
       0,    0, // properties
       0,    0, // enums/sets
       0,    0, // constructors
       0,       // flags
       0,       // signalCount

 // slots: name, argc, parameters, tag, flags
       1,    0,   39,    2, 0x0a /* Public */,
       3,    0,   40,    2, 0x0a /* Public */,
       4,    0,   41,    2, 0x0a /* Public */,
       5,    0,   42,    2, 0x0a /* Public */,
       6,    0,   43,    2, 0x0a /* Public */,

 // slots: parameters
    QMetaType::Void,
    QMetaType::Void,
    QMetaType::Void,
    QMetaType::Void,
    QMetaType::Void,

       0        // eod
};

void HS::qt_static_metacall(QObject *_o, QMetaObject::Call _c, int _id, void **_a)
{
    if (_c == QMetaObject::InvokeMetaMethod) {
        auto *_t = static_cast<HS *>(_o);
        (void)_t;
        switch (_id) {
        case 0: _t->clockChanged(); break;
        case 1: _t->copyClocks(); break;
        case 2: _t->pasteClocks(); break;
        case 3: _t->apply(); break;
        case 4: _t->applyDIO(); break;
        default: ;
        }
    }
    (void)_a;
}

QT_INIT_METAOBJECT const QMetaObject HS::staticMetaObject = { {
    QMetaObject::SuperData::link<TModule::staticMetaObject>(),
    qt_meta_stringdata_HS.data,
    qt_meta_data_HS,
    qt_static_metacall,
    nullptr,
    nullptr
} };


const QMetaObject *HS::metaObject() const
{
    return QObject::d_ptr->metaObject ? QObject::d_ptr->dynamicMetaObject() : &staticMetaObject;
}

void *HS::qt_metacast(const char *_clname)
{
    if (!_clname) return nullptr;
    if (!strcmp(_clname, qt_meta_stringdata_HS.stringdata0))
        return static_cast<void*>(this);
    return TModule::qt_metacast(_clname);
}

int HS::qt_metacall(QMetaObject::Call _c, int _id, void **_a)
{
    _id = TModule::qt_metacall(_c, _id, _a);
    if (_id < 0)
        return _id;
    if (_c == QMetaObject::InvokeMetaMethod) {
        if (_id < 5)
            qt_static_metacall(this, _c, _id, _a);
        _id -= 5;
    } else if (_c == QMetaObject::RegisterMethodArgumentMetaType) {
        if (_id < 5)
            *reinterpret_cast<int*>(_a[0]) = -1;
        _id -= 5;
    }
    return _id;
}
struct qt_meta_stringdata_LVDS_t {
    QByteArrayData data[6];
    char stringdata0[48];
};
#define QT_MOC_LITERAL(idx, ofs, len) \
    Q_STATIC_BYTE_ARRAY_DATA_HEADER_INITIALIZER_WITH_OFFSET(len, \
    qptrdiff(offsetof(qt_meta_stringdata_LVDS_t, stringdata0) + ofs \
        - idx * sizeof(QByteArrayData)) \
    )
static const qt_meta_stringdata_LVDS_t qt_meta_stringdata_LVDS = {
    {
QT_MOC_LITERAL(0, 0, 4), // "LVDS"
QT_MOC_LITERAL(1, 5, 12), // "clockChanged"
QT_MOC_LITERAL(2, 18, 0), // ""
QT_MOC_LITERAL(3, 19, 10), // "copyClocks"
QT_MOC_LITERAL(4, 30, 11), // "pasteClocks"
QT_MOC_LITERAL(5, 42, 5) // "apply"

    },
    "LVDS\0clockChanged\0\0copyClocks\0pasteClocks\0"
    "apply"
};
#undef QT_MOC_LITERAL

static const uint qt_meta_data_LVDS[] = {

 // content:
       8,       // revision
       0,       // classname
       0,    0, // classinfo
       4,   14, // methods
       0,    0, // properties
       0,    0, // enums/sets
       0,    0, // constructors
       0,       // flags
       0,       // signalCount

 // slots: name, argc, parameters, tag, flags
       1,    0,   34,    2, 0x0a /* Public */,
       3,    0,   35,    2, 0x0a /* Public */,
       4,    0,   36,    2, 0x0a /* Public */,
       5,    0,   37,    2, 0x0a /* Public */,

 // slots: parameters
    QMetaType::Void,
    QMetaType::Void,
    QMetaType::Void,
    QMetaType::Void,

       0        // eod
};

void LVDS::qt_static_metacall(QObject *_o, QMetaObject::Call _c, int _id, void **_a)
{
    if (_c == QMetaObject::InvokeMetaMethod) {
        auto *_t = static_cast<LVDS *>(_o);
        (void)_t;
        switch (_id) {
        case 0: _t->clockChanged(); break;
        case 1: _t->copyClocks(); break;
        case 2: _t->pasteClocks(); break;
        case 3: _t->apply(); break;
        default: ;
        }
    }
    (void)_a;
}

QT_INIT_METAOBJECT const QMetaObject LVDS::staticMetaObject = { {
    QMetaObject::SuperData::link<TModule::staticMetaObject>(),
    qt_meta_stringdata_LVDS.data,
    qt_meta_data_LVDS,
    qt_static_metacall,
    nullptr,
    nullptr
} };


const QMetaObject *LVDS::metaObject() const
{
    return QObject::d_ptr->metaObject ? QObject::d_ptr->dynamicMetaObject() : &staticMetaObject;
}

void *LVDS::qt_metacast(const char *_clname)
{
    if (!_clname) return nullptr;
    if (!strcmp(_clname, qt_meta_stringdata_LVDS.stringdata0))
        return static_cast<void*>(this);
    return TModule::qt_metacast(_clname);
}

int LVDS::qt_metacall(QMetaObject::Call _c, int _id, void **_a)
{
    _id = TModule::qt_metacall(_c, _id, _a);
    if (_id < 0)
        return _id;
    if (_c == QMetaObject::InvokeMetaMethod) {
        if (_id < 4)
            qt_static_metacall(this, _c, _id, _a);
        _id -= 4;
    } else if (_c == QMetaObject::RegisterMethodArgumentMetaType) {
        if (_id < 4)
            *reinterpret_cast<int*>(_a[0]) = -1;
        _id -= 4;
    }
    return _id;
}
struct qt_meta_stringdata_HEATERX_t {
    QByteArrayData data[10];
    char stringdata0[101];
};
#define QT_MOC_LITERAL(idx, ofs, len) \
    Q_STATIC_BYTE_ARRAY_DATA_HEADER_INITIALIZER_WITH_OFFSET(len, \
    qptrdiff(offsetof(qt_meta_stringdata_HEATERX_t, stringdata0) + ofs \
        - idx * sizeof(QByteArrayData)) \
    )
static const qt_meta_stringdata_HEATERX_t qt_meta_stringdata_HEATERX = {
    {
QT_MOC_LITERAL(0, 0, 7), // "HEATERX"
QT_MOC_LITERAL(1, 8, 12), // "clockChanged"
QT_MOC_LITERAL(2, 21, 0), // ""
QT_MOC_LITERAL(3, 22, 10), // "copyClocks"
QT_MOC_LITERAL(4, 33, 11), // "pasteClocks"
QT_MOC_LITERAL(5, 45, 5), // "apply"
QT_MOC_LITERAL(6, 51, 8), // "applyDIO"
QT_MOC_LITERAL(7, 60, 14), // "enablePlotting"
QT_MOC_LITERAL(8, 75, 15), // "disablePlotting"
QT_MOC_LITERAL(9, 91, 9) // "savePlots"

    },
    "HEATERX\0clockChanged\0\0copyClocks\0"
    "pasteClocks\0apply\0applyDIO\0enablePlotting\0"
    "disablePlotting\0savePlots"
};
#undef QT_MOC_LITERAL

static const uint qt_meta_data_HEATERX[] = {

 // content:
       8,       // revision
       0,       // classname
       0,    0, // classinfo
       8,   14, // methods
       0,    0, // properties
       0,    0, // enums/sets
       0,    0, // constructors
       0,       // flags
       0,       // signalCount

 // slots: name, argc, parameters, tag, flags
       1,    0,   54,    2, 0x0a /* Public */,
       3,    0,   55,    2, 0x0a /* Public */,
       4,    0,   56,    2, 0x0a /* Public */,
       5,    0,   57,    2, 0x0a /* Public */,
       6,    0,   58,    2, 0x0a /* Public */,
       7,    0,   59,    2, 0x0a /* Public */,
       8,    0,   60,    2, 0x0a /* Public */,
       9,    0,   61,    2, 0x0a /* Public */,

 // slots: parameters
    QMetaType::Void,
    QMetaType::Void,
    QMetaType::Void,
    QMetaType::Void,
    QMetaType::Void,
    QMetaType::Void,
    QMetaType::Void,
    QMetaType::Void,

       0        // eod
};

void HEATERX::qt_static_metacall(QObject *_o, QMetaObject::Call _c, int _id, void **_a)
{
    if (_c == QMetaObject::InvokeMetaMethod) {
        auto *_t = static_cast<HEATERX *>(_o);
        (void)_t;
        switch (_id) {
        case 0: _t->clockChanged(); break;
        case 1: _t->copyClocks(); break;
        case 2: _t->pasteClocks(); break;
        case 3: _t->apply(); break;
        case 4: _t->applyDIO(); break;
        case 5: _t->enablePlotting(); break;
        case 6: _t->disablePlotting(); break;
        case 7: _t->savePlots(); break;
        default: ;
        }
    }
    (void)_a;
}

QT_INIT_METAOBJECT const QMetaObject HEATERX::staticMetaObject = { {
    QMetaObject::SuperData::link<TModule::staticMetaObject>(),
    qt_meta_stringdata_HEATERX.data,
    qt_meta_data_HEATERX,
    qt_static_metacall,
    nullptr,
    nullptr
} };


const QMetaObject *HEATERX::metaObject() const
{
    return QObject::d_ptr->metaObject ? QObject::d_ptr->dynamicMetaObject() : &staticMetaObject;
}

void *HEATERX::qt_metacast(const char *_clname)
{
    if (!_clname) return nullptr;
    if (!strcmp(_clname, qt_meta_stringdata_HEATERX.stringdata0))
        return static_cast<void*>(this);
    return TModule::qt_metacast(_clname);
}

int HEATERX::qt_metacall(QMetaObject::Call _c, int _id, void **_a)
{
    _id = TModule::qt_metacall(_c, _id, _a);
    if (_id < 0)
        return _id;
    if (_c == QMetaObject::InvokeMetaMethod) {
        if (_id < 8)
            qt_static_metacall(this, _c, _id, _a);
        _id -= 8;
    } else if (_c == QMetaObject::RegisterMethodArgumentMetaType) {
        if (_id < 8)
            *reinterpret_cast<int*>(_a[0]) = -1;
        _id -= 8;
    }
    return _id;
}
struct qt_meta_stringdata_XVBIAS_t {
    QByteArrayData data[6];
    char stringdata0[50];
};
#define QT_MOC_LITERAL(idx, ofs, len) \
    Q_STATIC_BYTE_ARRAY_DATA_HEADER_INITIALIZER_WITH_OFFSET(len, \
    qptrdiff(offsetof(qt_meta_stringdata_XVBIAS_t, stringdata0) + ofs \
        - idx * sizeof(QByteArrayData)) \
    )
static const qt_meta_stringdata_XVBIAS_t qt_meta_stringdata_XVBIAS = {
    {
QT_MOC_LITERAL(0, 0, 6), // "XVBIAS"
QT_MOC_LITERAL(1, 7, 12), // "clockChanged"
QT_MOC_LITERAL(2, 20, 0), // ""
QT_MOC_LITERAL(3, 21, 10), // "copyClocks"
QT_MOC_LITERAL(4, 32, 11), // "pasteClocks"
QT_MOC_LITERAL(5, 44, 5) // "apply"

    },
    "XVBIAS\0clockChanged\0\0copyClocks\0"
    "pasteClocks\0apply"
};
#undef QT_MOC_LITERAL

static const uint qt_meta_data_XVBIAS[] = {

 // content:
       8,       // revision
       0,       // classname
       0,    0, // classinfo
       4,   14, // methods
       0,    0, // properties
       0,    0, // enums/sets
       0,    0, // constructors
       0,       // flags
       0,       // signalCount

 // slots: name, argc, parameters, tag, flags
       1,    0,   34,    2, 0x0a /* Public */,
       3,    0,   35,    2, 0x0a /* Public */,
       4,    0,   36,    2, 0x0a /* Public */,
       5,    0,   37,    2, 0x0a /* Public */,

 // slots: parameters
    QMetaType::Void,
    QMetaType::Void,
    QMetaType::Void,
    QMetaType::Void,

       0        // eod
};

void XVBIAS::qt_static_metacall(QObject *_o, QMetaObject::Call _c, int _id, void **_a)
{
    if (_c == QMetaObject::InvokeMetaMethod) {
        auto *_t = static_cast<XVBIAS *>(_o);
        (void)_t;
        switch (_id) {
        case 0: _t->clockChanged(); break;
        case 1: _t->copyClocks(); break;
        case 2: _t->pasteClocks(); break;
        case 3: _t->apply(); break;
        default: ;
        }
    }
    (void)_a;
}

QT_INIT_METAOBJECT const QMetaObject XVBIAS::staticMetaObject = { {
    QMetaObject::SuperData::link<TModule::staticMetaObject>(),
    qt_meta_stringdata_XVBIAS.data,
    qt_meta_data_XVBIAS,
    qt_static_metacall,
    nullptr,
    nullptr
} };


const QMetaObject *XVBIAS::metaObject() const
{
    return QObject::d_ptr->metaObject ? QObject::d_ptr->dynamicMetaObject() : &staticMetaObject;
}

void *XVBIAS::qt_metacast(const char *_clname)
{
    if (!_clname) return nullptr;
    if (!strcmp(_clname, qt_meta_stringdata_XVBIAS.stringdata0))
        return static_cast<void*>(this);
    return TModule::qt_metacast(_clname);
}

int XVBIAS::qt_metacall(QMetaObject::Call _c, int _id, void **_a)
{
    _id = TModule::qt_metacall(_c, _id, _a);
    if (_id < 0)
        return _id;
    if (_c == QMetaObject::InvokeMetaMethod) {
        if (_id < 4)
            qt_static_metacall(this, _c, _id, _a);
        _id -= 4;
    } else if (_c == QMetaObject::RegisterMethodArgumentMetaType) {
        if (_id < 4)
            *reinterpret_cast<int*>(_a[0]) = -1;
        _id -= 4;
    }
    return _id;
}
QT_WARNING_POP
QT_END_MOC_NAMESPACE
