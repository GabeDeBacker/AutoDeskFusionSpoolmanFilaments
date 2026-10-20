// Wait for Fusion to inject the API
function waitForAdsk(fusionReady) {
    if (typeof adsk !== "undefined") {
        console.log("adsk ready");
        fusionReady();
    } else {
        setTimeout(() =>waitForAdsk(fusionReady), 50);
    }
}

function sendToFusion(action, data) {
    if (typeof adsk !== "undefined") {
        if (data) {
            return adsk.fusionSendData(action, JSON.stringify(data));
        }
        return adsk.fusionSendData(action, JSON.stringify({}));
    } else {
        console.error("adsk is not ready");
    }
}

function setHandlers(handlers) {
    window.fusionJavaScriptHandler = {
      handle: function (action, data) {
        try {
          if (action === 'response') {
            return;
          }

          const jsonData = JSON.parse(data || '{}');
          const handler = handlers[action];
          if (handler) {
            return handler(jsonData);
          }
          console.log(`No handler found for action: ${action}`, jsonData);
        } catch (error) {
          console.log(`Error handling action: ${action}`, error);
        }
      }
    };
}