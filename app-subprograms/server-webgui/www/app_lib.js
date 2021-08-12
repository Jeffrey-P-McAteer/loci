/**
 * app-lib wrapper which communicates API calls over a websocket.
 * This should be used by all subprograms to perform state changes
 * and UI modifications in a standardized way.
 */

'use strict';

/**
 * Memory + Functions beginning with "_" are to be considered private and internal to the lib;
 * they may change at any time and will not always do the same thing.
 */
class app_lib {
  static app_base_url = location.protocol+'//'+location.hostname+(location.port ? ':'+location.port: '');
  // if browser sorts [1,4,2,3] => [1,2,3,4] this is false,
  //    else if sorts [1,4,2,3] => [4,3,2,1] this is true.
  static client_sorts_left_right = undefined;
  static ws = null;
  
  static connect_to_server() {
    if (app_lib.ws === null || app_lib.ws.readyState === WebSocket.CLOSED) {
      app_lib.ws = new WebSocket(app_lib.app_base_url.replace('http', 'ws')+'/ws');
      app_lib.ws.onopen = app_lib.ws_onopen;
      app_lib.ws.onmessage = app_lib.ws_onmessage;
    }
  }

  static sorts_left_right() {
    if (app_lib.client_sorts_left_right === undefined) {
      var nums = [1,4,2,3];
      nums.sort(c => c);
      // Thie browser sorts large -> small
      if (nums[0] > nums[1]) {
        app_lib.client_sorts_left_right = true;
      }
      else {
        app_lib.client_sorts_left_right = false;
      }
    }
    return app_lib.client_sorts_left_right;
  }

  static ws_onopen() {
    // Were we previously connected?
    console.log('// TODO attempt re-connect using previous nonce (server ignores if invalid)');
  }

  static ws_onmessage(event) {
    var data_dict = JSON.parse(event.data);
    console.log('onmessage', data_dict);
  }

  static ws_send(data_dict) {
    if (!util_isDict(data_dict)) {
      throw 'Data sent to ws_send() is not a dictionary!';
    }
    app_lib.connect_to_server();
    app_lib.ws.send(JSON.stringify(data_dict));
  }

  /*
   * Private functionality below.
   */

  static _existing_menu = {};
  static _create_menu_item(translated_menu_path, weight, on_click_js, menu_root=null) {
    if (menu_root == null) {
      if (!('elm_ul' in app_lib._existing_menu)) {
        app_lib._existing_menu['elm_ul'] = document.getElementById('sm-menu');
      }
      menu_root = app_lib._existing_menu;
    }
    var dis_name = translated_menu_path.shift();
    var must_create_new = !(dis_name in menu_root);
    if (must_create_new) {
      menu_root[dis_name] = {};
      menu_root[dis_name]['elm'] = document.createElement('li');
      menu_root[dis_name]['elm_a'] = document.createElement('a');
      
      menu_root[dis_name]['elm_a'].innerText = dis_name;
      menu_root[dis_name]['elm_a'].href = '#';

      menu_root[dis_name]['elm'].appendChild(menu_root[dis_name]['elm_a']);

      if (translated_menu_path.length < 1) {
        menu_root[dis_name]['elm'].setAttribute('weight', weight);
      }

      menu_root['elm_ul'].appendChild(menu_root[dis_name]['elm']);

      // re-sort children by element weights
      app_lib._sort_children_by_weight( menu_root['elm_ul'] );

    }

    if (translated_menu_path.length > 0) {
      // We are at a sub-menu, create <ul> + pass down
      if (must_create_new) {
        menu_root[dis_name]['elm_ul'] = document.createElement('ul');
        menu_root[dis_name]['elm'].appendChild(menu_root[dis_name]['elm_ul']);
      }
      app_lib._create_menu_item(translated_menu_path, weight, on_click_js, menu_root[dis_name]);
    }
    else {
      // We have reached a root menu item, edit the <a> tag!
      menu_root[dis_name]['weight'] = weight;
      menu_root[dis_name]['elm_a'].href = 'javascript:'+on_click_js;

      // Allow SM library to re-bind to menu items
      app_gui_init_sm();

    }
  }

  static _create_left_tab(translated_name, weight, on_click_js, is_focused, css) {
    var app_left_tabs = document.getElementById('app_left_tabs');
    app_lib._create_tab_within(app_left_tabs, translated_name, weight, on_click_js, is_focused, css);
  }

  static _create_right_tab(translated_name, weight, on_click_js, is_focused, css) {
    var app_right_tabs = document.getElementById('app_right_tabs');
    app_lib._create_tab_within(app_right_tabs, translated_name, weight, on_click_js, is_focused, css);
  }

  static _create_tab_within(tabs_parent, translated_name, weight, on_click_js, is_focused, css) {
    var new_tab = document.createElement('a');
    new_tab.href = 'javascript:'+on_click_js;
    new_tab.innerText = translated_name;
    new_tab.style = css;
    new_tab.setAttribute('weight', weight);
    
    new_tab.onclick = function(evt) {
      [].forEach.call(tabs_parent.children, function(el) {
          el.classList.remove('focused');
      });
      new_tab.classList.add('focused');
    };

    if (is_focused) {
      [].forEach.call(tabs_parent.children, function(el) {
          el.classList.remove('focused');
      });
      new_tab.classList.add('focused');
    }

    tabs_parent.appendChild(new_tab);
    app_lib._sort_children_by_weight(tabs_parent);
  }

  static _left_nav_to(url) {
    document.getElementById('app_active_left_tab').src = url;
  }

  static _right_nav_to(url) {
    document.getElementById('app_active_right_tab').src = url;
  }

  static _sort_children_by_weight(parent_elm) {
    var default_weight = '500';
    
    var children = parent_elm.children;
    // Sort children (browser-specific because of dumb sort rules)
    var sortedChildren = [].slice.call(children);
    if (app_lib.sorts_left_right()) {
      sortedChildren.sort(c => -1 * parseInt(c.getAttribute('weight') || default_weight, 10));
    }
    else {
      sortedChildren.sort(c => parseInt(c.getAttribute('weight') || default_weight, 10));
    }

    // Remove children
    while (parent_elm.firstChild) {
      parent_elm.removeChild(parent_elm.lastChild);
    }
    
    // Add in sorted order
    sortedChildren.forEach(function (p) {
        parent_elm.appendChild(p);
    });
  }

}

// Whoever includes this will cause the library to try connecting to the server within the next 100ms
setTimeout(app_lib.connect_to_server, 100);

