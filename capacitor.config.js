/** @type {import('@capacitor/core').CapacitorConfig} */
const config = {
  appId: 'in.nyaymitra.app',
  appName: 'NYAYMITRA 2.0',
  webDir: 'web',
  server: {
    url: undefined,
    cleartext: true,
  },
  plugins: {
    SplashScreen: {
      launchShowDuration: 2000,
      backgroundColor: '#070c18',
      showSpinner: false,
    },
    StatusBar: {
      style: 'DARK',
      backgroundColor: '#070c18',
    },
    Keyboard: {
      resize: 'body',
      style: 'DARK',
    },
  },
};

module.exports = config;
