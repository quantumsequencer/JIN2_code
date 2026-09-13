// Copyright 2026 Sony Global Manufacturing & Operations Corporation

namespace Sony.Jin.Gateway
{
    using System;
    using System.Diagnostics;
    using System.IO;
    using System.Linq;
    using System.Reflection;
    using System.Threading;
    using System.Threading.Tasks;
    using System.Windows;
    using System.Windows.Threading;
    using Microsoft.Extensions.DependencyInjection;
    using Reactive.Bindings.Extensions;
    using Sony.Jin.Gateway.Data;
    using Sony.Jin.Gateway.Models;
    using Sony.Jin.Gateway.Properties;
    using Sony.Jin.Gateway.ViewModels;
    using Sony.Jin.Gateway.Views;
    using Sony.Jin.Shared;

    /// <summary>
    /// App.xaml の相互作用ロジック
    /// </summary>
    public partial class App : Application
    {
        private const string ConfigFileName = "config.json";
        private Logger logger = null;
        private JsonHolder<AppSettings> settingsHolder = null;
        private InjectionManager injectionManager = null;

        /// <inheritdoc cref="IServiceProvider.GetService(Type)"/>
        public T GetRequiredService<T>() => this.injectionManager.GetRequiredService<T>();

        /// <inheritdoc/>
        protected override void OnStartup(StartupEventArgs e)
        {
            // 重複起動を検知した場合、終了する。
            ExitIfDuplicateLaunch();

            this.ExitIfException(() =>
            {
                // 起動シーケンス第1段階を開始する。ログ出力が出来ない起動シーケンス第1段階で例外が発生した場合、異常事態により終了する。
                var entryDir = Directory.GetParent(Assembly.GetEntryAssembly().Location).ToString();

                // (1) アプリケーションログ開始
                var targetDir = Path.Combine(entryDir, "logs");
                this.logger = Logger.Create(targetDir) ?? throw new InvalidOperationException("Unable to setup application logger.");
                this.logger.Info("Application started.");

                // (2) 環境・定義ファイル読み込み
                var configHolder = new JsonHolder<AppConfig>(Path.Combine(entryDir, ConfigFileName));
                configHolder.Save();   // config.json がない状態から起動したときに既定値のファイルを保存する目的で実行。

                // (3) 設定ファイル読み込み
                this.settingsHolder = new JsonHolder<AppSettings>(Path.Combine(entryDir, configHolder.Data.SettingsFileName));

                // (4) 文言リソースの読み込み
                _ = JsonResourceManager.Instance;

                // (5) スレッドプールの設定: 同時にアクティブにできるスレッド数を拡大する。
                ThreadPool.GetMinThreads(out var defaultMinWorkerThreads, out var defaultMinCompletionPortThreads);
                var appliedValue = Math.Max(configHolder.Data.MinWorkerThreads, defaultMinWorkerThreads);  // 実際に設定される値が元々の環境よりも下回らないように Math.Max() を取ってから設定する。
                ThreadPool.SetMinThreads(appliedValue, defaultMinCompletionPortThreads);

                this.injectionManager = new InjectionManager(this.logger, configHolder.Data, this.settingsHolder.Data);
                this.injectionManager.GetRequiredService<IMainModel>().Initialize();
            });

            AppDomain.CurrentDomain.UnhandledException += (s, eventArgs) =>
            {
                // UI スレッドで catch されなかった例外をログに記録する。
                this.logger.Error(string.Format("UnhandledException: terminating = {0}, exception = {1}", eventArgs.IsTerminating, eventArgs.ExceptionObject.ToString()));
                if (eventArgs.ExceptionObject is Exception exception)
                {
                    this.logger.Exception("(Main Thread: unknown)", "(unknown)", exception);
                }
            };

            base.OnStartup(e);
        }

        /// <summary>
        /// MainWindow の Loaded イベント時に実行する処理（class MainWindow から呼び出す）
        /// </summary>
        public void OnMainWindowLoaded()
        {
            // Window を生成する処理は必ずこの後に行う。さもないと Application.Current.MainWindow が
            // MainWindow クラスインスタンスでなくなるリスクがあり、
            // App.xaml で設定しているプロパティ ShutdownMode="OnMainWindowClose" の前提が崩れる。
            // また、MainWindow をできるだけ早く表示させ、利用者の不安を高めないようにする。
            _ = this.injectionManager.GetRequiredService<LiveCurrentGraphWindow>();
            _ = this.injectionManager.GetRequiredService<LiveHardwareGraphWindow>();
            _ = this.injectionManager.GetRequiredService<LoopbackWindow>();
            _ = this.injectionManager.GetRequiredService<OptionsWindow>();
            _ = this.injectionManager.GetRequiredService<SnapCurrentGraphWindow>();
            _ = this.injectionManager.GetRequiredService<SnapHardwareGraphWindow>();
            _ = this.injectionManager.GetRequiredService<StubWindow>();

            var activationTask = Task.Run(() =>
            {
                try
                {
                    // 起動シーケンス第2段階を開始する。念のため、すべての例外を catch してログに記録するようにする。
                    this.injectionManager.GetRequiredService<IMainModel>().Activate();
                }
                catch (Exception e)
                {
                    this.logger.Exception("MainModel.Activate", "none", e);
                }
            });

            this.MainWindow.Closing += (s, e) =>
            {
                // 起動処理完了までメイン画面クローズを延期する。
                if (!activationTask.IsCompleted)
                {
                    e.Cancel = true;
                    Action action = () => this.MainWindow.Close();
                    activationTask.ContinueWith(_ => this.Dispatcher.BeginInvoke(DispatcherPriority.Normal, action));
                }
            };
        }

        /// <inheritdoc/>
        protected override void OnExit(ExitEventArgs e)
        {
            // 終了シーケンスを開始する。
            this.injectionManager.GetRequiredService<IMainModel>().Deactivate();

            base.OnExit(e);

            this.injectionManager?.Dispose();
            this.injectionManager = null;

            this.settingsHolder.Save();

            this.logger.Info("Application terminated.");
            this.logger?.Dispose();
            this.logger = null;
        }

        private static void ExitIfDuplicateLaunch()
        {
            var current = Process.GetCurrentProcess();
            var array = Process.GetProcessesByName(current.ProcessName);
            if (!array.Any(x => x.Id != current.Id && x.MainModule.FileName == current.MainModule.FileName)) return;

            var message = string.Format("Another {0} process is running simultaneously.", current.ProcessName);
            MessageBox.Show(message, "Startup Error", MessageBoxButton.OK, MessageBoxImage.Error);

            Environment.Exit(1);
        }

        private void ExitIfException(Action action)
        {
            try
            {
                action?.Invoke();
            }
            catch (Exception e)
            {
                MessageBox.Show(e.Message, "Startup Error", MessageBoxButton.OK, MessageBoxImage.Error);

                this.logger?.Exception("App.OnStartup", "none", e);
                this.logger?.Info("Application terminated.");
                this.logger?.Dispose();
                this.logger = null;

                Environment.Exit(1);
            }
        }

        private class InjectionManager : DisposableBase
        {
            private readonly ServiceProvider diProvider = null;

            public InjectionManager(ILogger logger, AppConfig config, AppSettings settings)
            {
                var diServices = new ServiceCollection();

                // 引数のインスタンスをそのまま service collection に登録
                // 注意: IDisposable が実装されていると diProvider.Dispose() 時にまとめて Dispose() されるため、
                //       渡す値インスタンスは IDisposalbe を継承していないか、重複して Dispose() 可能なものに限る。
                diServices.AddSingleton<ILogger>(logger);
                diServices.AddSingleton<AppConfig>(config);
                diServices.AddSingleton<AppSettings>(settings);

                diServices.AddSingleton(x => new LiveCurrentGraphWindow(x.GetRequiredService<LiveCurrentGraphViewModel>()));
                diServices.AddSingleton(x => new LiveHardwareGraphWindow(x.GetRequiredService<LiveHardwareGraphViewModel>()));
                diServices.AddSingleton(x => new LoopbackWindow(x.GetRequiredService<LoopbackViewModel>()));
                diServices.AddSingleton(x => new OptionsWindow(x.GetRequiredService<OptionsViewModel>()));
                diServices.AddSingleton(x => new SnapCurrentGraphWindow(x.GetRequiredService<SnapCurrentGraphViewModel>()));
                diServices.AddSingleton(x => new SnapHardwareGraphWindow(x.GetRequiredService<SnapHardwareGraphViewModel>()));
                diServices.AddSingleton(x => new StubWindow(x.GetRequiredService<StubViewModel>()));
                diServices.AddSingleton<LiveCurrentGraphViewModel, LiveCurrentGraphViewModel>();
                diServices.AddSingleton<LiveHardwareGraphViewModel, LiveHardwareGraphViewModel>();
                diServices.AddSingleton<LoopbackViewModel, LoopbackViewModel>();
                diServices.AddSingleton<MainViewModel, MainViewModel>();
                diServices.AddSingleton<OptionsViewModel, OptionsViewModel>();
                diServices.AddSingleton<SnapCurrentGraphViewModel, SnapCurrentGraphViewModel>();
                diServices.AddSingleton<SnapHardwareGraphViewModel, SnapHardwareGraphViewModel>();
                diServices.AddSingleton<StubViewModel, StubViewModel>();
                diServices.AddSingleton<ILinkModel, LinkModel>();
                diServices.AddSingleton<ILiveCurrentGraphModel, LiveCurrentGraphModel>();
                diServices.AddSingleton<ILiveHardwareGraphModel, LiveHardwareGraphModel>();
                diServices.AddSingleton<ILoopbackModel, LoopbackModel>();
                diServices.AddSingleton<IMainModel, MainModel>();
                diServices.AddSingleton<IPortModel, PortModel>();
                diServices.AddSingleton<IRecordModel, RecordModel>();
                diServices.AddSingleton<IRootModel, RootModel>();
                diServices.AddSingleton<ISnapCurrentGraphModel, SnapCurrentGraphModel>();
                diServices.AddSingleton<ISnapHardwareGraphModel, SnapHardwareGraphModel>();
                diServices.AddSingleton<IStubDebugPortModel, StubDebugPortModel>();
                diServices.AddSingleton<IStubHostPortModel, StubHostPortModel>();
                diServices.AddSingleton<IStubLogPortModel, StubLogPortModel>();

                this.diProvider = diServices.BuildServiceProvider().AddTo(this.CompositeDisposable);
            }

            public T GetRequiredService<T>() => this.diProvider.GetRequiredService<T>();
        }
    }
}
