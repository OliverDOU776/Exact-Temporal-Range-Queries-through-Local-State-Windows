"use strict";
importScripts("solver.js?v=usable-demo-20261109a");
self.onmessage = ({ data }) => {
  const id = data && data.id;
  try {
    self.postMessage({ id, result: self.LSWDemo.solve(data && data.payload) });
  } catch (error) {
    self.postMessage({ id, error: error instanceof Error ? error.message : String(error) });
  }
};
