import QtQuick
import QtQuick.Effects

RectangularShadow {
  anchors.fill: parent
  z: -1
  radius: parent && "radius" in parent ? parent.radius : 12
  blur: 22
  spread: 0
  offset: Qt.vector2d(0, 5)
  color: Qt.rgba(0, 0, 0, 0.16)
}
