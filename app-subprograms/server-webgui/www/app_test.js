/**
 * This script is used to test the JS API provided to graphics requesters.
 * DO NOT INCLUDE UNLESS TESTING!
 */

function app_spawn_test_api_calls() {

  setTimeout(function() {
    app_lib._create_left_tab('Hello World', 100, 'app_lib._left_nav_to("example.org");', false, null);
    app_lib._create_menu_item(['File', 'Submenu', 'Quit'], 100, 'alert(1);');
    app_lib._create_menu_item(['File', 'Submenu', 'Settings'], 50, 'alert(1);');
    app_lib._create_menu_item(['Edit', 'BeforeGarbage', 'Number100'], 100, 'alert(2);');
    app_lib._create_menu_item(['Edit', 'Garbage', 'Number900'], 900, 'alert(2);');
    app_lib._create_menu_item(['Edit', 'Garbage', 'Number50'], 50, 'alert(2);');
    app_lib._create_menu_item(['Edit', 'Garbage', 'Number0'], 0, 'alert(2);');
    app_lib._create_menu_item(['Edit', 'Garbage', 'Number51'], 51, 'alert(2);');
    app_lib._create_menu_item(['Edit', 'Garbage', 'Number100'], 100, 'alert(2);');
    app_lib._create_menu_item(['Edit', 'Garbage', 'Number999'], 999, 'alert(2);');
    app_lib._create_menu_item(['Edit', 'AfterGarbage', 'Number100'], 100, 'alert(2);');

  }, 500);

  setTimeout(function() {
    app_lib._create_left_tab('SMS', 110, 'app_lib._left_nav_to("//bing.com");', true, null);
    app_lib._create_right_tab('Map', 300, 'app_lib._right_nav_to("//google.com");', true, null);
    app_lib._create_right_tab('Self', 110, 'app_lib._right_nav_to("//worldwind.arc.nasa.gov/");', true, null);
    app_lib._create_right_tab('End', 400, 'app_lib._right_nav_to("google.com");', false, null);
    app_lib._create_menu_item(['File', 'Address Book'], 50, 'alert(1);');
  }, 600);

  setTimeout(function() {
    app_lib._create_left_tab('Chat', 110, 'app_lib._left_nav_to("bing.com");', false, null);
  }, 600);

}

document.addEventListener('DOMContentLoaded', app_spawn_test_api_calls);

