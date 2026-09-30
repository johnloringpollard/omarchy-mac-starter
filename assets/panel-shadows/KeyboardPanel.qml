import QtQuick
import qs.Ui as Ui

Ui.KeyboardPanel {
  PanelShadow {
    // The inherited default slot is the content holder inside the card.
    Component.onCompleted: parent = parent.parent
  }
}
