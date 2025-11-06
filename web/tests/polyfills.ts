// Polyfill for ArrayBuffer.prototype.resizable (required by webidl-conversions@8.0.0)
// This property is only available in Node.js 20+, but jsdom requires it
// This must be loaded before jsdom/webidl-conversions is imported
if (typeof ArrayBuffer !== 'undefined' && !Object.getOwnPropertyDescriptor(ArrayBuffer.prototype, 'resizable')) {
  Object.defineProperty(ArrayBuffer.prototype, 'resizable', {
    get: function() {
      return false;
    },
    configurable: true,
    enumerable: false,
  });
}

