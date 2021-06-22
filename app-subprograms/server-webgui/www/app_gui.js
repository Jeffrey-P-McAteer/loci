/**
 * Responsible for setting up callbacks to poll "gui" DB tables
 * and render passive UI (menu tree, left+right tabs, action buttons, notifications).
 * Relies on app_lib.js.
 */

function initialize_gui() {
  // Setup split.js for left + right areas
  var left_initial_percent = parse_float_or(get_client_prop('left-split-percent'), 25.0);
  if (parse_bool_or(get_client_prop('left-collapsed'), false)) {
    left_initial_percent = 0;
  }
  window.app_split = Split(
    [document.getElementById('area_left'), document.getElementById('area_right'), ],
    {
      direction: 'horizontal',
      /* percentage values */
      sizes: [left_initial_percent, 100-left_initial_percent],
      /* pixel values */
      maxSize: [800, Infinity],
      minSize: [0, 0],
      gutterSize: 18,
      expandToMin: true,
      // Add a tap/click handler to toggle between 0px and 200px
      // before gutter HTMLElement is added to DOM.
      gutter: function(index, direction, pairElement) {
        let g = document.createElement('div');
        g.classList.add('gutter');
        g.classList.add('gutter-horizontal');
        g.addEventListener('dblclick', function (ev) {
          let is_collapsed = window.app_split.getSizes()[0] < 3;
          if (is_collapsed) {
            var left_initial_percent = parse_float_or(get_client_prop('left-split-percent'), 25.0);
            window.app_split.setSizes([left_initial_percent, 100-left_initial_percent]);
            set_client_prop('left-collapsed', 'false');
          }
          else {
            set_client_prop('left-split-percent', window.app_split.getSizes()[0]);
            set_client_prop('left-collapsed', 'true');
            window.app_split.setSizes([0, 100]);
          }
        });
        return g;
      },
      // Record current left offset in percent using set_client_prop('left-split-percent', VAL)
      onDragEnd: function(sizes) {
        let is_collapsed = sizes[0] < 3;
        if (!is_collapsed) {
          set_client_prop('left-split-percent', sizes[0]);
        }
      },
    }
  );


  // Setup smartmenus.js
  app_gui_init_sm();

}

function app_gui_init_sm() {
  // See https://www.smartmenus.org/wp-content/cache/all/docs/index.html
  $('#sm-menu').smartmenus({
    subMenusSubOffsetX: 1,
    subMenusSubOffsetY: -8,
    subIndicators: false,

  });
}

document.addEventListener('DOMContentLoaded', initialize_gui);

