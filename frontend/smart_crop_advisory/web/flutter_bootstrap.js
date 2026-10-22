{{flutter_js}}
{{flutter_build_config}}

// Load Flutter's renderer from the app's own static assets. This keeps the
// web app working in local and offline environments that cannot reach gstatic.
_flutter.loader.load({
  config: {
    canvasKitBaseUrl: 'canvaskit/',
  },
});
