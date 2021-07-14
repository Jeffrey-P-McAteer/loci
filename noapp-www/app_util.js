/**
 * Responsible for utilities not specific enough to go anywhere else.
 */

function util_isDict(v) {
    return typeof v==='object' && v!==null && !(v instanceof Array) && !(v instanceof Date);
}

/**
 * Query LocalStorage for key/value string data,
 * returning "" on any errors.
 */
function get_client_prop(pkey) {
  var val = '';
  try {
    var val = localStorage.getItem(pkey);
  }
  catch (err) { }
  if (!val) {
    val = '';
  }
  return val;
}

/**
 * Write LocalStorage
 */
function set_client_prop(pkey, value) {
  localStorage.setItem(pkey, value);
}


function parse_float_or(possible_float_s, default_val) {
  try {
    var v = parseFloat(possible_float_s);
    if (!(v === null) && !Number.isNaN(v)) {
      return v;
    }
  }
  catch (err) { }
  return default_val;
}

function parse_bool_or(possible_bool_s, default_val) {
  try {
    if (!(possible_bool_s === null) && possible_bool_s.length > 0) {
      possible_bool_s = possible_bool_s.toLowerCase();
      if (possible_bool_s === 'true' || possible_bool_s === 't' || possible_bool_s === '0') {
        return true;
      }
      if (possible_bool_s === 'false' || possible_bool_s === 'f' || possible_bool_s === '1') {
        return false;
      }
    }
  }
  catch (err) { }
  return default_val;
}

// callback accepts (status_code, data) assuming data can be JSON-decoded.
function http_get_json(url, callback) {
  var xhr = new XMLHttpRequest();
  xhr.open('GET', url, true);
  xhr.responseType = 'json';
  xhr.onload = function() {
    var decoded_data = null;
    try {
      decoded_data = JSON.parse(xhr.response);
    }
    catch (err) { console.log(err); }
    callback(xhr.status, decoded_data);
  };
  xhr.send();
}



