# -*- coding: utf-8 -*-
# Copyright: Michal Krassowski <krassowski.michal@gmail.com>
# License: GNU GPL, version 3 or later; http://www.gnu.org/copyleft/gpl.html
"""
This plugin adds the function of touchscreen, similar that one implemented in AnkiDroid.

It adds a "view" menu entity (if it doesn't exist) with options like:

    switching touchscreen
    modifying some of the colors


If you want to contribute visit GitHub page: https://github.com/krassowski/Anki-TouchScreen
Also, feel free to send me bug reports or feature requests.

Copyright: Michal Krassowski <krassowski.michal@gmail.com>
License: GNU GPL, version 3 or later; http://www.gnu.org/copyleft/gpl.html,
Important parts of Javascript code inspired by http://creativejs.com/tutorials/painting-with-pixels/index.html
"""

__addon_name__ = "TouchScreen"
__version__ = "0.2.6"

from aqt import mw, dialogs
from aqt.utils import showWarning


from anki.lang import _
from anki.hooks import addHook

from PyQt5.QtWidgets import QAction, QMenu, QColorDialog, QMessageBox, QInputDialog
from PyQt5 import QtCore
from PyQt5.QtGui import QKeySequence
from PyQt5.QtGui import QColor
from PyQt5.QtCore import pyqtSlot as slot

# This declarations are there only to be sure that in case of troubles
# with "profileLoaded" hook everything will work.

ts_state_on = False
ts_profile_loaded = False
ts_pen_mode = True

ts_color = "#272828"
ts_line_width = 1
ts_width_eraser = 1
ts_opacity = 1.0
ts_factor_frame = 1
ts_default_review_html = mw.reviewer.revHtml


@slot()
def ts_change_color():
    """
    Open color picker and set chosen color to text (in content)
    """
    global ts_color
    qcolor_old = QColor(ts_color)
    qcolor = QColorDialog.getColor(qcolor_old)
    if qcolor.isValid():
        ts_color = qcolor.name()
        execute_js("color = '" + ts_color + "'; update_pen_settings()")
        ts_refresh()


@slot()
def ts_change_width():
    global ts_line_width
    value, accepted = QInputDialog.getDouble(mw, "Touch Screen", "Enter the width:", ts_line_width)
    if accepted:
        ts_line_width = value
        execute_js("line_width = '" + str(ts_line_width) + "'; update_pen_settings()")
        ts_refresh()


@slot()
def ts_change_opacity():
    global ts_opacity
    value, accepted = QInputDialog.getDouble(mw, "Touch Screen", "Enter the opacity (0 = transparent, 100 = opaque):", 100 * ts_opacity, 0, 100, 2)
    if accepted:
        ts_opacity = value / 100
        execute_js("canvas.style.opacity = " + str(ts_opacity))
        ts_refresh()


@slot()
def ts_pen_mode():
    global ts_pen_mode
    if (ts_pen_mode):
        ts_pen_mode = False;
        ts_menu_pen_mode.setChecked(False);
        execute_js("pen_mode = false")
    else:
        ts_pen_mode = True;
        ts_menu_pen_mode.setChecked(True);
        execute_js("pen_mode = true")


@slot()
def ts_change_factor_frame():
    global ts_factor_frame
    value, accepted = QInputDialog.getInt(mw, "Touch Screen", "Enter the number of frames skipped between each pointer's frame:", ts_factor_frame, 1, 100, 10)
    if accepted:
        ts_factor_frame = value
        execute_js("factor_frame = '" + str(ts_factor_frame) + "'; update_pen_settings()")
        ts_refresh()


@slot()
def ts_change_width_eraser():
    global ts_width_eraser
    value, accepted = QInputDialog.getDouble(mw, "Touch Screen", "Enter the width of the eraser:", 2*ts_width_eraser)
    if accepted:
        ts_width_eraser = value/2
        execute_js("width_eraser = '" + str(ts_width_eraser) + "'; update_pen_settings()")
        ts_refresh()

@slot()
def ts_about():
    """
    Show "about" window.
    """
    ts_about_box = QMessageBox()
    ts_about_box.setText(__addon_name__ + " " + __version__ + __doc__)
    ts_about_box.setGeometry(300, 300, 250, 150)
    ts_about_box.setWindowTitle("About " + __addon_name__ + " " + __version__)

    ts_about_box.exec_()
	

def ts_save():
    """
    Saves configurable variables into profile, so they can
    be used to restore previous state after Anki restart.
    """
    mw.pm.profile['ts_state_on'] = ts_state_on;
    mw.pm.profile['ts_color'] = ts_color;
    mw.pm.profile['ts_line_width'] = ts_line_width;
    mw.pm.profile['ts_opacity'] = ts_opacity;
    """mw.pm.profilr['ts_pen_mode'] = ts_pen_mode"""
    """mw.pm.profilr['ts_factor_frame'] = ts_factor_frame"""
    """mw.pm.profilr['ts_width_eraser'] = ts_width_eraser"""


def ts_load():
    """
    Load configuration from profile, set states of checkable menu objects
    and turn on night mode if it were enabled on previous session.
    """
    global ts_state_on, ts_color, ts_profile_loaded, ts_line_width, ts_opacity

    try:
        ts_state_on = mw.pm.profile['ts_state_on']
        ts_color = mw.pm.profile['ts_color']
        ts_line_width = mw.pm.profile['ts_line_width']
        ts_opacity = mw.pm.profile['ts_opacity']
        """ts_pen_mode = mw.pm.profile['ts_pen_mode']"""
        """ts_factor_frame = mw.pm.profile['ts_factor_frame']"""
        """ts_width_eraser = mw.pm.profile['ts_width_eraser']"""
    except KeyError:
        ts_state_on = False
        ts_color = "#f0f"
        ts_line_width = 1.0
        ts_opacity = 1.0
        """ts_pen_mode = True"""
        """ts_factor_frame = 10"""
        """ts_width_eraser = 1"""
    ts_profile_loaded = True

    if ts_state_on:
        ts_on()

    assure_plugged_in()


def execute_js(code):
    web_object = mw.reviewer.web
    web_object.eval(code)


def assure_plugged_in():
    global ts_default_review_html

    if not mw.reviewer.revHtml == custom:
        ts_default_review_html = mw.reviewer.revHtml
        mw.reviewer.revHtml = custom


def clear_blackboard(web_object=None):
    assure_plugged_in()

    if not web_object: 
        web_object = mw.reviewer.web

    if ts_state_on:
        javascript = 'clear_canvas();'
        web_object.eval(javascript)


def ts_resize(html, card, context):
    if ts_state_on:
        html += """
        <script>
        var ts_interval;
        if(ts_interval === undefined){
            if(resize !== undefined)
                ts_interval = window.setInterval(resize, 750);
        }
        </script>
        """
    return html


def ts_onload():
    """
    Add hooks and initialize menu.
    Call to this function is placed on the end of this file.
    """

    addHook("unloadProfile", ts_save)
    addHook("profileLoaded", ts_load)
    addHook("showQuestion", clear_blackboard)
    addHook('prepareQA', ts_resize)
    ts_setup_menu()


ts_blackboard = u"""
<div id="canvas_wrapper">
    <canvas id="main_canvas" width="100" height="100"></canvas>
</div>
<div id="pencil_button_bar">
    <input type="button" class="active" onclick="switch_mode();" value="\u270e" title="Change mode of the pointer" id="ts_mode_button">
    <input type="button" onclick="ts_undo();" value="\u21B6" title="Undo the last stroke" id="ts_undo_button">
    <input type="button" class="active" onclick="clear_canvas();" value="\u2715" title="Clean whiteboard">
    <input type="button" class="active" onclick="active=!active;switch_visibility();switch_class(this, 'active');" value="\u2bbf" title="Toggle visiblity">
</div>

<style>
#canvas_wrapper, #main_canvas
{
    position:absolute;
    top: 0px;
    left: 0px;
    z-index: 999;
}
#main_canvas{
    opacity: """ + str(ts_opacity) + """;
}
.night_mode #pencil_button_bar input[type=button].active
{
    color: #fff!important;
}
#pencil_button_bar input[type=button].active
{
    color: black!important;
}
#pencil_button_bar
{
    position: fixed;
    top: 45%;
    left: 1px;
    z-index: 1000;
    font-family: "Arial Unicode MS", unifont, "Everson Mono", tahoma, arial;
}

#pencil_button_bar input[type=button]
{
    border: 1px solid black;
    margin: 0 1px;
    display: flex;
    flex-direction: column;
    width: 50px!important;
    font-size: 160%;
    line-height: 150%;
    align-items: center;
    height: 50px;
    border-radius: 8px;
    background-color: rgba(250,250,250,0.5)!important;
    color: black;
    color: #ccc!important;
}

.night_mode #pencil_button_bar input[type=button]{
    background-color: rgba(10,10,10,0.5)!important;
    border-color: #ccc;
    color: #444!important;
    text-shadow: 0 0 1px rgba(5, 5, 5, 0.9);
}
#canvas_wrapper
{
    height: 100px
}
</style>

<script>
var visible = true;
var canvas = document.getElementById('main_canvas');
var wrapper = document.getElementById('canvas_wrapper');
var ts_undo_button = document.getElementById('ts_undo_button');
var ts_mode_button = document.getElementById('ts_mode_button');
var ctx = canvas.getContext('2d');
var arrays_of_points = [ ];
var points = [ ];
var color = '#fff';
var line_width = 1;

canvas.onselectstart = function() { return false; };
wrapper.onselectstart = function() { return false; };

function switch_visibility()
{
    if (visible)
    {
        canvas.style.display='none';
    }
    else
    {
        canvas.style.display='block';
    }
    visible = !visible;
}


function midPointBtw(p1, p2) {
  return {
    x: p1.x + (p2.x - p1.x) / 2,
    y: p1.y + (p2.y - p1.y) / 2
  };
}

function clear_canvas()
{
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    arrays_of_points=[];
}

function switch_class(e,c)
{
    var reg = new RegExp('(\\\s|^)' + c + '(\\s|$)');
    if (e.className.match(new RegExp('(\\s|^)' + c + '(\\s|$)')))
    {
        e.className = e.className.replace(reg, '');
    }
    else
    {
        e.className += c;
    }
}

function switch_mode() {
	if (ts_mode_button.value == "\u270e") {
		ts_mode_button.value = "\u25b1";
	} else {
	    ts_mode_button.value = "\u270e";
	}
}

function resize() {
    var card = document.getElementsByClassName('card')[0]
    ctx.canvas.width = document.documentElement.scrollWidth - 1;
    ctx.canvas.height = Math.max(
        document.body.clientHeight,
        window.innerHeight,
        document.documentElement ? document.documentElement.scrollHeight : 0,
        card ? card.scrollHeight : 0
    ) - 1;

    canvas.style.height = ctx.canvas.height + 'px';
    wrapper.style.width = ctx.canvas.width + 'px';
    update_pen_settings()
}

window.setTimeout(resize, 0)
window.addEventListener('resize', resize);
document.body.addEventListener('load', resize)

var isMouseDown = false;
var mouseX = 0;
var mouseY = 0;
var active = true;


function update_pen_settings(){
    ctx.lineJoin = ctx.lineCap = 'round';
    ctx.lineWidth = line_width;
    ctx.strokeStyle = color;
    ts_redraw()
}

canvas.addEventListener("pointerdown",function (e) {
    if(!isMouseDown) {
		isMouseDown = true;
		event.preventDefault();
		if (ts_mode_button.value == "\u270e") {
			arrays_of_points.push(new Array());
			arrays_of_points[arrays_of_points.length-1].push({ x: e.offsetX, y: e.offsetY });
			update_pen_settings();
			ts_undo_button.className = "active";
		}
		else {
			points[0] = new Array();
		}
	}
});

function ts_undo(){
    arrays_of_points.pop()
    if(!arrays_of_points.length)
    {
        ts_undo_button.className = ""
    }
    ts_redraw()
}


var width_eraser = 1;


function ts_erase(points){
    for (var j = 0; j < points[0].length-1; j++) {
        var pe1 = points[0][j];
        var pe2 = points[0][j+1];
        var x1 = pe1.x;
        var y1 = pe1.y;
        var x3 = pe2.x;
        var y3 = pe2.y;
        for (var path = 0; path < arrays_of_points.length; path++) {
            for (var k = 0, len = arrays_of_points[path].length; k < len-1; k++) {
                var p1 = arrays_of_points[path][k];
                var p2 = arrays_of_points[path][k+1];
                var x2 = p1.x;
                var x4 = p2.x;
                var y2 = p1.y;
                var y4 = p2.y;
                var t = ((x2 - x4)*(y4 - y3) - (x4 - x3)*(y2 - y4))/((y1 - y3)*(x2 - x4) - (y2 - y4)*(x1 - x3));
                var t2 = ((x1 - x3)*(y4 - y3) - (x4 - x3)*(y1 - y3))/((y1 - y3)*(x2 - x4) - (y2 - y4)*(x1 - x3));
                //if (((t <= width_eraser && t >= 0) || (t >= -width_eraser && t <= 0)) && ((t2 <= width_eraser && t2 >= 0) || (t2 >= -width_eraser && t2 <= 0))) {
                //    arrays_of_points.splice(path, 1);
                //}
				if ((t <= width_eraser && t >= -width_eraser) && (t2 <= width_eraser && t2 >= -width_eraser)) {
                    arrays_of_points.splice(path, 1);
					if(!arrays_of_points.length) {
						ts_undo_button.className = ""
					}
                }
            }
        }
    }
    ts_redraw()
}

window.addEventListener("pointerup",function (e) {
	if(isMouseDown) {
		index = 0;
		isMouseDown = false;
	}
});


function ts_redraw()
{
    ctx.clearRect(0, 0, ctx.canvas.width, ctx.canvas.height);
    for (var path = 0; path < arrays_of_points.length; path++) {
        var p1 = arrays_of_points[path][0];
        var p2 = arrays_of_points[path][1];
        ctx.beginPath();
        ctx.moveTo(p1.x, p1.y);
        for (var i = 1, len = arrays_of_points[path].length; i < len; i++) {
            var midPoint = midPointBtw(p1, p2);
            ctx.quadraticCurveTo(p1.x, p1.y, midPoint.x, midPoint.y);
            //ctx.lineTo(p1.x, p1.y);
            p1 = arrays_of_points[path][i];
            p2 = arrays_of_points[path][i+1];
        }
        //ctx.lineTo(p1.x, p1.y);
        ctx.stroke();
    }

}

function ts_redraw2(index_last_point)
{
    for (var path = index_last_point; path < arrays_of_points.length; path++) {
        var p1 = arrays_of_points[path][0];
        var p2 = arrays_of_points[path][1];
        ctx.beginPath();
        ctx.moveTo(p1.x, p1.y);
        for (var i = 1, len = arrays_of_points[path].length; i < len; i++) {
            var midPoint = midPointBtw(p1, p2);
            ctx.quadraticCurveTo(p1.x, p1.y, midPoint.x, midPoint.y);
            //ctx.lineTo(p1.x, p1.y);
            p1 = arrays_of_points[path][i];
            p2 = arrays_of_points[path][i+1];
        }
        //ctx.lineTo(p1.x, p1.y);
		ctx.stroke();
    }

}

var index = 0;
var factor_frame = 10;
var pen_mode = true;

function applied_frame_factor() {
	if(pen_mode){
		return factor_frame;
	}else{
		return 2;
	}
}
 
canvas.addEventListener("pointermove", function (e) {
	index++;
	if(isMouseDown && index%applied_frame_factor() == 0) {
		if (active && ts_mode_button.value == "\u270e") {
			var index_last_point = arrays_of_points.length-1;
			var distAll = 0;
			try {
			var distX = e.offsetX - arrays_of_points[arrays_of_points.length-1][arrays_of_points[arrays_of_points.length-1].length-1].x;
			var distY = e.offsetY - arrays_of_points[arrays_of_points.length-1][arrays_of_points[arrays_of_points.length-1].length-1].y;
			distAll = (distX*distX) + (distY*distY);
			}finally{
				try {
					if (distAll <= 10000) {
						arrays_of_points[arrays_of_points.length-1].push({ x: e.offsetX, y: e.offsetY });
					}
				}catch(error){
					
				}
			}
			ts_redraw2(index_last_point);
		}
		else if (ts_mode_button.value != "\u270e") {
			points[0].push({ x: e.offsetX, y: e.offsetY });
			ts_erase(points);
		}
		index = 0;
	}
});

document.addEventListener('keyup', function(e) {
    // Z or z
    if ((e.keyCode == 90 || e.keyCode == 122) && e.altKey) {
        ts_undo()
    }
})

</script>
"""


def custom(*args, **kwargs):
    global ts_state_on
    default = ts_default_review_html(*args, **kwargs)
    if not ts_state_on:
        return default
    output = (
        default +
        ts_blackboard + 
        "<script>color = '" + ts_color + "'</script>" +
        "<script>line_width = '" + str(ts_line_width) + "'</script>"
    )
    return output


mw.reviewer.revHtml = custom


def ts_on():
    """
    Turn on
    """
    if not ts_profile_loaded:
        showWarning(TS_ERROR_NO_PROFILE)
        return False

    global ts_state_on
    ts_state_on = True
    ts_menu_switch.setChecked(True)
    return True


def ts_off():
    """
    Turn off
    """
    if not ts_profile_loaded:
        showWarning(TS_ERROR_NO_PROFILE)
        return False

    global ts_state_on
    ts_state_on = False
    ts_menu_switch.setChecked(False)
    return True


@slot()
def ts_switch():
    """
    Switch TouchScreen.
    """

    if ts_state_on:
        ts_off()
    else:
        ts_on()

    # Reload current screen.

    if mw.state == "review":
        mw.moveToState('overview')
        mw.moveToState('review')
    if mw.state == "deckBrowser":
        mw.deckBrowser.refresh()
    if mw.state == "overview":
        mw.overview.refresh()


def ts_refresh():
    """
    Refresh display by reenabling night or normal mode.
    """
    if ts_state_on:
        ts_on()
    else:
        ts_off()


def ts_setup_menu():
    """
    Initialize menu. If there is an entity "View" in top level menu
    (shared with other plugins, like "Zoom" of R. Sieker) options of
    the addon will be placed there. In other case it creates that menu.
    """
    global ts_menu_switch
    global ts_menu_pen_mode

    try:
        mw.addon_view_menu
    except AttributeError:
        mw.addon_view_menu = QMenu(_(u"&View"), mw)
        mw.form.menubar.insertMenu(mw.form.menuTools.menuAction(),
                                    mw.addon_view_menu)

    mw.ts_menu = QMenu(_('&Touchscreen'), mw)

    mw.addon_view_menu.addMenu(mw.ts_menu)

    ts_menu_switch = QAction(_('&Enable touchscreen mode'), mw, checkable=True)
    ts_menu_color = QAction(_('Set &pen color'), mw)
    ts_menu_width = QAction(_('Set pen &width'), mw)
    ts_menu_opacity = QAction(_('Set pen &opacity'), mw)
    ts_menu_pen_mode = QAction(_('Set pen &pen mode'), mw, checkable=True)
    ts_menu_factor_frame = QAction(_('Set pen &factor frame'), mw)
    ts_menu_width_eraser = QAction(_('Set pen &width eraser'), mw)	
    ts_menu_about = QAction(_('&About...'), mw)

    ts_toggle_seq = QKeySequence("Ctrl+r")
    ts_menu_switch.setShortcut(ts_toggle_seq)

    mw.ts_menu.addAction(ts_menu_switch)
    mw.ts_menu.addAction(ts_menu_color)
    mw.ts_menu.addAction(ts_menu_width)
    mw.ts_menu.addAction(ts_menu_opacity)
    mw.ts_menu.addAction(ts_menu_pen_mode)
    mw.ts_menu.addAction(ts_menu_factor_frame)
    mw.ts_menu.addAction(ts_menu_width_eraser)
    mw.ts_menu.addSeparator()
    mw.ts_menu.addAction(ts_menu_about)
    mw.ts_menu.addSeparator()

    ts_menu_switch.triggered.connect(ts_switch)
    ts_menu_color.triggered.connect(ts_change_color)
    ts_menu_width.triggered.connect(ts_change_width)
    ts_menu_opacity.triggered.connect(ts_change_opacity)
    ts_menu_pen_mode.triggered.connect(ts_pen_mode)
    ts_menu_factor_frame.triggered.connect(ts_change_factor_frame)
    ts_menu_width_eraser.triggered.connect(ts_change_width_eraser)
    ts_menu_about.triggered.connect(ts_about)
    
    ts_menu_pen_mode.setChecked(True)

TS_ERROR_NO_PROFILE = "No profile loaded"

#
# ONLOAD SECTION
#

ts_onload()
