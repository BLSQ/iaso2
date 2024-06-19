const path = require('path');
const webpack = require('webpack');
const BundleTracker = require('webpack-bundle-tracker');
const MiniCssExtractPlugin = require('mini-css-extract-plugin');
// Switch here for french
// remember to switch in webpack.dev.js and
// django settings as well
const LOCALE = 'fr';
module.exports = {
    // fail the entire build on 'module not found'
    bail: true,
    context: __dirname,
    mode: 'production',
    target: ['web', 'es2015'],
    entry: {
        common: ['react', 'react-dom', 'react-intl', 'typescript'],
        iaso: './assets/js/apps/Iaso/index',
        superset: './assets/js/supersetSDK',
    },

    stats: {
        children: true,
    },
    output: {
        path: path.resolve(__dirname, './assets/webpack'),
        filename: '[name]-[chunkhash].js',
        publicPath: '',
        assetModuleFilename: 'assets/[name].[hash][ext][query]',
    },
    devtool: 'source-map',

    plugins: [
        new webpack.NormalModuleReplacementPlugin(
            /^__intl\/messages\/en$/,
            '../translations/en.json',
        ),
        new webpack.NormalModuleReplacementPlugin(
            /^__intl\/messages\/fr$/,
            '../translations/fr.json',
        ),
        new BundleTracker({
            filename: path.resolve(
                __dirname,
                './assets/webpack/webpack-stats-prod.json',
            ),
        }),
        new MiniCssExtractPlugin({ filename: '[name]-[chunkhash].css' }),
        new webpack.DefinePlugin({
            'process.env': {
                // This has effect on the react lib size
                // need to do JSON stringify on all vars here to take effect,
                // see https://github.com/eHealthAfrica/guinea-connect-universal-app/blob/development/webpack/prod.config.js
                NODE_ENV: JSON.stringify('production'),
            },
            __LOCALE: JSON.stringify(LOCALE),
        }),
        // Minification
        new webpack.LoaderOptionsPlugin({ minimize: true }),
        new webpack.WatchIgnorePlugin({
            paths: [/\.d\.ts$/],
        }),
    ],

    optimization: {
        minimize: true, // old UglifyJsPlugin
        splitChunks: {
            // old CommonsChunkPlugin
            cacheGroups: {
                commons: {
                    // name: 'commons',
                    // chunks: 'initial',
                    minChunks: 3,
                },
            },
        },
        // runtimeChunk: true,
        // concatenateModules: true // old ModuleConcatenationPlugin
    },
    module: {
        rules: [
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
                            plugins: [
                                [
                                    'formatjs',
                                    {
                                        messagesDir: path.join(
                                            __dirname,
                                            '/assets/messages',
                                        ),
                                    },
                                ],
                            ],
                        },
                    },
                ],
            },
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
                                [
                                    '@babel/preset-typescript',
                                    { isTSX: true, allExtensions: true },
                                ],
                                '@babel/preset-react',
                            ],
                            plugins: [
                                [
                                    'formatjs',
                                    {
                                        messagesDir: path.join(
                                            __dirname,
                                            '/assets/messages',
                                        ),
                                    },
                                ],
                            ],
                        },
                    },
                ],
            },
            // Extract Sass files
            {
                test: /\.scss$/,
                use: [
                    { loader: MiniCssExtractPlugin.loader },
                    { loader: 'css-loader' },
                    { loader: 'sass-loader' },
                ],
            },
            {
                test: /\.css$/,
                use: [MiniCssExtractPlugin.loader, 'css-loader'],
            },
            {
                test: /\.(png|jpg|jpeg|gif|svg)$/,
                type: 'asset/resource',
            },
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

    // https://github.com/SheetJS/js-xlsx/issues/285

    externals: [{ './cptable': 'var cptable' }],

    resolve: {
        alias: {
            'react/jsx-runtime': 'react/jsx-runtime.js',
        },
        fallback: {
            fs: false,
        },
        /* assets/js/apps path allow using absolute import eg: from 'iaso/libs/Api' */
        modules: ['node_modules', path.resolve(__dirname, 'assets/js/apps/')],
        extensions: ['.js', '.jsx', '.ts', '.tsx'],
    },
};
