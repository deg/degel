function initialize() {
  var mapOptions = {
    zoom: 15,
	
    center: new google.maps.LatLng(31.740123,34.981047),
    mapTypeControl: true,
	overviewMapControl:true,
    rotateControl:true,    
   	mapTypeControlOptions: {
	style: google.maps.MapTypeControlStyle.HORIZONTAL_BAR,
	position: google.maps.ControlPosition.TOP_LEFT
    },
    panControl: true,
    panControlOptions: {
        position: google.maps.ControlPosition.TOP_LEFT
    },
    zoomControl: true,
    zoomControlOptions: {
        style: google.maps.ZoomControlStyle.LARGE,
        position: google.maps.ControlPosition.TOP_RIGHT
    },
    scaleControl: true,
    
  }
  var map = new google.maps.Map(document.getElementById('map-canvas'),
                                mapOptions);
	  var marker = new google.maps.Marker({
      position: new google.maps.LatLng(31.740123,34.981047),
      map: map,
      title: 'Degel Headquarters'
  });
}

google.maps.event.addDomListener(window, 'load', initialize);







