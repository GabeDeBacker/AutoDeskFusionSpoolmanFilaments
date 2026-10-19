// Wait for Fusion to inject the API
function waitForAdsk(fusionReady) {
    if (typeof adsk !== "undefined") {
        console.log("adsk ready");
        fusionReady();
    } else {
        setTimeout(() =>waitForAdsk(fusionReady), 50);
    }
}