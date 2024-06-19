require('dotenv').config();
const { CleanWebpackPlugin } = require('clean-webpack-plugin');

const path = require('path');
const webpack = require('webpack');
const BundleTracker = require('webpack-bundle-tracker');
// Switch here for French. This is set to 'en' in dev to not get react-intl warnings
// remember to switch in webpack.prod.js and
// django settings as well
const LOCALE = 'fr';
// If you launch the dev server with `WEBPACK_HOST=192.168.1.XXX  npm run dev`
// where 192.168.1.XXX is your local IP address, you can access the dev server
// from another device on the same network, typically from a mobile device or tablet
const WEBPACK_HOST = process.env.WEBPACK_HOST || 'localhost';
const WEBPACK_PORT = process.env.WEBPACK_PORT || '3000';
const WEBPACK_PROTOCOL = process.env.WEBPACK_PROTOCOL || 'http';
const WEBPACK_URL = `${WEBPACK_PROTOCOL}://${WEBPACK_HOST}:${WEBPACK_PORT}`;
const WEBPACK_PATH =
    process.env.WEBPACK_PATH || path.resolve(__dirname, './assets/webpack/');

const oldBrowsersConfig = [
    {
        test: /\.(ts|tsx)?$/,
        exclude: /node_modules/,
        use: [
            {
                loader: 'babel-loader',
                options: {
                    cacheDirectory: true,
                    presets: [
                        [
                            '@babel/preset-env',
                            {
                                targets: {
                                    node: '12',
                                    chrome: '55',
                                    ie: '11',
                                },
                                include: [
                                    '@babel/plugin-transform-optional-chaining',
                                    '@babel/plugin-transform-nullish-coalescing-operator',
                                    '@babel/plugin-transform-numeric-separator',
                                    '@babel/plugin-transform-logical-assignment-operators',
                                    '@babel/plugin-transform-destructuring',
                                ],
                            },
                        ],
                        '@babel/preset-react',
                        [
                            '@babel/preset-typescript',
                            { isTSX: true, allExtensions: true },
                        ],
                    ],
                    plugins: ['@babel/transform-runtime', 'formatjs'],
                },
            },
        ],
    },
    {
        test: /\.js?$/,
        include: [
            path.resolve(__dirname, '../node_modules/react-leaflet'),
            path.resolve(__dirname, '../node_modules/@react-leaflet'),
            path.resolve(__dirname, '../node_modules/@dnd-kit'),
            path.resolve(__dirname, '../plugins'),
            path.resolve(__dirname, 'assets'),
        ],
        use: [
            {
                loader: 'babel-loader',
                options: {
                    presets: [
                        [
                            '@babel/preset-env',
                            {
                                targets: {
                                    node: '12',
                                    chrome: '55',
                                    ie: '11',
                                },
                                include: [
                                    '@babel/plugin-transform-optional-chaining',
                                    '@babel/plugin-transform-nullish-coalescing-operator',
                                    '@babel/plugin-transform-numeric-separator',
                                    '@babel/plugin-transform-logical-assignment-operators',
                                    '@babel/plugin-transform-destructuring',
                                ],
                            },
                        ],
                        '@babel/preset-react',
                    ],
                    plugins: ['@babel/transform-runtime', 'formatjs'],
                },
            },
        ],
    },
];
const newBrowsersConfig = [
    {
        test: /\.(ts|tsx)?$/,
        exclude: /node_modules/,
        use: [
            {
                loader: 'babel-loader',
                options: {
                    // cacheDirectory: true,
                    presets: [
                        ['@babel/preset-env', { targets: { node: '14' } }],
                        '@babel/preset-react',
                        [
                            '@babel/preset-typescript',
                            { isTSX: true, allExtensions: true },
                        ],
                    ],
                    plugins: ['@babel/transform-runtime', 'formatjs'],
                },
            },
        ],
    },
    {
        test: /\.js?$/,
        exclude: /node_modules/,
        use: [
            {
                loader: 'babel-loader',
                options: {
                    presets: ['@babel/preset-env', '@babel/preset-react'],
                    plugins: ['@babel/transform-runtime', 'formatjs'],
                },
            },
        ],
    },
];

module.exports = {
    context: __dirname,
    mode: 'development',
    target: 'web',
    entry: {
        // use same settings as in Prod
        common: [
            'react',
            'bluesquare-components',
            'react-dom',
            'react-intl',
            '@mui/material',
            // Don't include, it packs all the icon instead of actually used one
            // '@mui/icons-material',
            '@mui/lab',
            '@mui/x-date-pickers',
            'lodash',
            'moment',
            'leaflet',
            'leaflet-draw',
            'prop-types',
            'typescript',
            'video.js',
        ],
        // styles: ['./assets/css/index.scss'],
        iaso: {
            dependOn: 'common',
            import: './assets/js/apps/Iaso/index',
        },
        superset: {
            import: './assets/js/supersetSDK',
        },
    },

    output: {
        path: WEBPACK_PATH,
        filename: '[name].js',
        sourceMapFilename: '[name].[contenthash].js.map',
        publicPath: ``, // Tell django to use this URL to load packages and not use STATIC_URL + bundle_name
        assetModuleFilename: 'assets/[name].[hash][ext][query]',
    },
    devtool: 'source-map',

    // config for webpack-dev-server
    devServer: {
        historyApiFallback: true,
        headers: {
            'Access-Control-Allow-Origin': '*',
        },
        host: '0.0.0.0',
        port: 3000,
        hot: true,
        devMiddleware: {
            writeToDisk: true,
        },
        static: {
            directory: path.join(__dirname, 'assets'),
            publicPath: '/',
        },
        client: {
            overlay: true,
            progress: true,
        },
        watchFiles: {
            paths: ['src/**/*', 'assets/**/*'],
            options: {
                usePolling: true,
            },
        },
    },

    plugins: [
        new webpack.HotModuleReplacementPlugin(),
        new CleanWebpackPlugin(),
        new webpack.NormalModuleReplacementPlugin(
            /^__intl\/messages\/en$/,
            '../translations/en.json',
        ),
        new webpack.NormalModuleReplacementPlugin(
            /^__intl\/messages\/fr$/,
            '../translations/fr.json',
        ),
        new webpack.NoEmitOnErrorsPlugin(), // don't reload if there is an error
        new BundleTracker({
            filename: `${WEBPACK_PATH}/webpack-stats.json`,
        }),
        new webpack.DefinePlugin({
            __LOCALE: JSON.stringify(LOCALE),
        }),
        // XLSX
        new webpack.IgnorePlugin({ resourceRegExp: /cptable/ }),
        new webpack.IgnorePlugin({
            resourceRegExp: /^perf_hooks$/,
        }),
    ],

    module: {
        rules: [
            {
                test: /\.(js|ts|tsx)$/,
                enforce: 'pre',
                use: ['source-map-loader'],
                exclude: /node_modules/,
            },
            ...(process.env.OLD_BROWSER === 'true'
                ? oldBrowsersConfig
                : newBrowsersConfig),
            {
                test: /\.css$/,
                use: [{ loader: 'style-loader' }, { loader: 'css-loader' }],
            },
            {
                test: /\.(png|jpg|jpeg|gif|svg)$/,
                type: 'asset/resource',
            },
            // Extract Sass files
            {
                test: /\.scss$/,
                use: [
                    { loader: 'style-loader' },
                    { loader: 'css-loader' },
                    { loader: 'sass-loader' },
                ],
            },
            // font files
            {
                test: /\.woff(\?v=\d+\.\d+\.\d+)?$/,
                type: 'asset/resource',
                generator: {
                    filename: 'fonts/[name].[hash][ext]',
                },
            },
            {
                test: /\.woff2(\?v=\d+\.\d+\.\d+)?$/,
                type: 'asset/resource',
                generator: {
                    filename: 'fonts/[name].[hash][ext]',
                },
            },
            {
                test: /\.ttf(\?v=\d+\.\d+\.\d+)?$/,
                type: 'asset/resource',
                generator: {
                    filename: 'fonts/[name].[hash][ext]',
                },
            },
            {
                test: /\.eot(\?v=\d+\.\d+\.\d+)?$/,
                type: 'asset/resource',
                generator: {
                    filename: 'fonts/[name].[hash][ext]',
                },
            },
            {
                test: /\.mp4$/,
                type: 'asset/resource',
                generator: {
                    filename: 'videos/[name].[hash][ext]',
                },
            },
            {
                test: /\.mjs$/,
                type: 'javascript/auto',
                use: 'babel-loader',
            },
        ],
        noParse: [require.resolve('typescript/lib/typescript.js')], // remove warning: https://github.com/microsoft/TypeScript/issues/39436
    },
    externals: [{ './cptable': 'var cptable' }],

    resolve: {
        alias: {
            'react/jsx-runtime': 'react/jsx-runtime.js',
            // see LIVE_COMPONENTS feature in doc
            ...(process.env.LIVE_COMPONENTS === 'true' && {
                'bluesquare-components': path.resolve(
                    __dirname,
                    '../../bluesquare-components/src/',
                ),
            }),
        },
        fallback: {
            fs: false,
        },
        modules:
            process.env.LIVE_COMPONENTS === 'true'
                ? [
                      'node_modules',
                      '../../bluesquare-components/node_modules/',
                      path.resolve(__dirname, 'assets/js/apps/'),
                  ]
                : /* assets/js/apps path allow using absolute import eg: from 'iaso/libs/Api' */
                  ['node_modules', path.resolve(__dirname, 'assets/js/apps/')],

        extensions: ['.js', '.jsx', '.ts', '.tsx'],
    },
    stats: {
        errorDetails: true,
    },
    ignoreWarnings: [
        {
            module: /typescript/,
            message: /the request of a dependency is an expression/,
        },
    ],
};
