/** @type {import('next').NextConfig} */
const nextConfig = {};
const nodeExternals = require("webpack-node-externals");

module.exports = nextConfig;

// next.config.js
module.exports = {
  // ... rest of the configuration.
  output: "standalone",
  images: {
    domains: ['http://corvid.westeurope.azurecontainer.io/','https://corvid.westeurope.azurecontainer.io/'],
  },
};
