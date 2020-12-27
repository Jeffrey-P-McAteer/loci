
// called by body onload
function main() {
  $("#menu").menu({position: {at: "left bottom"}});
  $('div.split-pane').splitPane();

  window.wwd = new WorldWind.WorldWindow("map0");
  
  // "offline" - just points to 3rdparty/worldwind-web/images/BMNG_world.topo.bathy.200405.3.2048x1024.jpg
  window.wwd.addLayer(new WorldWind.BMNGOneImageLayer());
  // Online, high-res landsat from NASA
  //window.wwd.addLayer(new WorldWind.BMNGLandsatLayer());

  window.wwd.globe.projection = new WorldWind.ProjectionMercator();

  window.placemarkLayer = new WorldWind.RenderableLayer("Placemarks");
  window.wwd.addLayer(window.placemarkLayer);

  // Online, high-res tutorial layer (just as a demo for now)
  // {
  //   // Web Map Tiling Service information from
  //   var serviceAddress = "https://map1.vis.earthdata.nasa.gov/wmts-webmerc/wmts.cgi?&request=GetCapabilities";
  //   // Layer displaying Gridded Population of the World density forecast
  //   var layerIdentifier = "GPW_Population_Density_2020";

  //   // Called asynchronously to parse and create the WMTS layer
  //   var createLayer = function (xmlDom) {
  //       // Create a WmtsCapabilities object from the XML DOM
  //       var wmtsCapabilities = new WorldWind.WmtsCapabilities(xmlDom);
  //       // Retrieve a WmtsLayerCapabilities object by the desired layer name
  //       var wmtsLayerCapabilities = wmtsCapabilities.getLayer(layerIdentifier);
  //       // Form a configuration object from the WmtsLayerCapabilities object
  //       var wmtsConfig = WorldWind.WmtsLayer.formLayerConfiguration(wmtsLayerCapabilities);
  //       // Create the WMTS Layer from the configuration object
  //       var wmtsLayer = new WorldWind.WmtsLayer(wmtsConfig);

  //       // Add the layers to WorldWind and update the layer manager
  //       window.wwd.addLayer(wmtsLayer);
  //       //layerManager.synchronizeLayerList();
  //   };

  //   // Called if an error occurs during WMTS Capabilities document retrieval
  //   var logError = function (jqXhr, text, exception) {
  //       console.log("There was a failure retrieving the capabilities document: " + text + " exception: " + exception);
  //   };

  //   $.get(serviceAddress).done(createLayer).fail(logError);
  // }

  // Online, high-res cached layer (currently under development)
  {
    // Web Map Tiling Service information from
    var serviceAddress = "http://localhost:8001/geoserver/gwc/service/wmts?&request=GetCapabilities";
    // Layer displaying Gridded Population of the World density forecast
    var layerIdentifier = "topp:states";

    // Called asynchronously to parse and create the WMTS layer
    var createLayer = function (xmlDom) {
        console.log('xmlDom', xmlDom);
        // Create a WmtsCapabilities object from the XML DOM
        var wmtsCapabilities = new WorldWind.WmtsCapabilities(xmlDom);
        // Retrieve a WmtsLayerCapabilities object by the desired layer name
        var wmtsLayerCapabilities = wmtsCapabilities.getLayer(layerIdentifier);
        console.log('wmtsLayerCapabilities', wmtsLayerCapabilities);
        // Form a configuration object from the WmtsLayerCapabilities object
        var wmtsConfig = WorldWind.WmtsLayer.formLayerConfiguration(wmtsLayerCapabilities);

        // TODO better general-purpose heuristic for matricies we can display
        console.log('wmtsConfig', wmtsConfig);
        wmtsConfig.tileMatrixSet = wmtsLayerCapabilities.capabilities.contents.tileMatrixSet[3];
        // for some reason {style} is not replaced in URLs, looks like a bug in WW
        wmtsConfig.resourceUrl = wmtsConfig.resourceUrl.replace("{style}", wmtsConfig.style);
        console.log('wmtsLayerCapabilities.capabilities.contents.tileMatrixSet', wmtsLayerCapabilities.capabilities.contents.tileMatrixSet);
        console.log('wmtsConfig.tileMatrixSet', wmtsConfig.tileMatrixSet);

        // Create the WMTS Layer from the configuration object
        var wmtsLayer = new WorldWind.WmtsLayer(wmtsConfig);

        // Add the layers to WorldWind and update the layer manager
        window.wwd.addLayer(wmtsLayer);
        //layerManager.synchronizeLayerList();
    };

    // Called if an error occurs during WMTS Capabilities document retrieval
    var logError = function (jqXhr, text, exception) {
        console.log("There was a failure retrieving the capabilities document: " + text + " exception: " + exception);
    };

    $.get(serviceAddress).done(createLayer).fail(logError);
  }

  window.wwd.addLayer(new WorldWind.CompassLayer());
  window.wwd.addLayer(new WorldWind.CoordinatesDisplayLayer(window.wwd));
  window.wwd.addLayer(new WorldWind.ViewControlsLayer(window.wwd));

  // Setup websocket comms + poll database for devices
  setup_ws();

  // Pollws every 5 seconds for devices, posreps, etc.
  setInterval(poll_ws, 5000);

}

function setup_ws() {
  var ws_url = '';
  if (window.location.protocol === "https:") {
    ws_url += 'wss://';
  }
  else {
    ws_url += 'ws://';
  }
  ws_url += window.location.host + '/ws';
  console.log('ws_url', ws_url);

  window.ws = new WebSocket(ws_url);

  window.ws.onopen = function(e) {
    // Do a poll immediately
    poll_ws();
  };
  window.ws.onclose = function(e) {
    // schedule a re-open in 5 seconds
    setTimeout(setup_ws, 5000);
  };
  window.ws.onmessage = on_ws_msg;
  window.ws.onerror = function(e) {
    console.log(e);
    // schedule a re-open in 5 seconds
    setTimeout(setup_ws, 5000);
  };

}

function on_ws_msg(msg) {
  console.log('on_ws_msg', msg);
  eval(msg.data);
}


function poll_ws() {

  window.ws.send(JSON.stringify({
    'type': 'db-query-constant',
    'query': 'select * from pos_reps ORDER BY ts DESC, id ASC limit 20;',
    'callback': 'show_posrep',
  }));


}


function show_posrep(data) {
  console.log('show_posrep', data);
  for (var i=0; i<data.length; i++) {
    console.log('show_posrep['+i+']', data[i]);

    var attrs = new WorldWind.PlacemarkAttributes(null);
    
    attrs.imageOffset = new WorldWind.Offset(
      WorldWind.OFFSET_FRACTION, 0.3,
      WorldWind.OFFSET_FRACTION, 0.0);
    attrs.labelAttributes.color = WorldWind.Color.YELLOW;
    attrs.labelAttributes.offset = new WorldWind.Offset(
            WorldWind.OFFSET_FRACTION, 0.5,
            WorldWind.OFFSET_FRACTION, 1.0);

    attrs.imageSource = WorldWind.configuration.baseUrl + "images/pushpins/plain-red.png";

    var p = new WorldWind.Placemark(
      new WorldWind.Position(data["lat"], data["lon"], 100.0), false, attrs
    );
    p.displayName = data["id"];
    p.label = data["id"];
    p.altitudeMode = WorldWind.RELATIVE_TO_GROUND;
    p.alwaysOnTop = true;

    window.placemarkLayer.addRenderable(p);

  }

  // Trim window.placemarkLayer.renderables
  while (window.placemarkLayer.renderables.length > 20) {
    window.placemarkLayer.renderables.shift();
  }

}

