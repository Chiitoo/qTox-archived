/* SPDX-License-Identifier: GPL-3.0-or-later
 * Copyright © 2015-2019 by The qTox Project Contributors
 * Copyright © 2024 The TokTok team.
 */
#pragma once

#include "src/video/videomode.h"
#include <QPair>
#include <QString>
#include <QVector>

#ifndef Q_OS_MACOS
#error "This file is only meant to be compiled for macOS targets"
#endif

namespace avfoundation {
const QString CAPTURE_SCREEN{"Capture screen"};

QVector<VideoMode> getDeviceModes(QString devName);
QVector<QPair<QString, QString>> getDeviceList();
} // namespace avfoundation
