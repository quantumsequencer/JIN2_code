// Copyright 2026 Sony Global Manufacturing & Operations Corporation

namespace Sony.Jin.Gateway.Models
{
    using System;
    using System.Collections.Generic;
    using System.Diagnostics;
    using System.Globalization;
    using System.IO;
    using System.Reactive.Disposables;
    using System.Reactive.Linq;
    using System.Reactive.Subjects;
    using System.Reflection;
    using System.Runtime.CompilerServices;
    using System.Text;
    using System.Threading.Tasks;
    using Reactive.Bindings;
    using Reactive.Bindings.Extensions;
    using Sony.Jin.Gateway.Data;
    using Sony.Jin.Gateway.Properties;
    using Sony.Jin.Shared;

    /// <inheritdoc cref="IRecordModel"/>
    internal class RecordModel : DisposableBase, IRecordModel
    {
        private readonly TaskCompletionSource<string> setDirectoryCompletion = new TaskCompletionSource<string>();
        private readonly Subject<object> foloderDialogRequest = null;
        private readonly ControlLinkLogger controlLinkLogger = null;
        private readonly TextPortLogger debugPortTxLogger = null;
        private readonly TextPortLogger debugPortRxLogger = null;
        private readonly TextPortLogger logPortRxLogger = null;
        private readonly HostPortLogger hostPortRxLogger = null;
        private readonly ObservableSetting<string> baseDirectory = null;
        private readonly ILogger logger = null;
        private readonly AppConfig config = null;
        private readonly IRootModel rootModel = null;
        private string directoryPath = null;

        /// <summary>
        /// Initializes a new instance of the <see cref="RecordModel"/> class.
        /// </summary>
        /// <param name="logger">ILogger</param>
        /// <param name="config">AppConfig</param>
        /// <param name="settings">AppSettings</param>
        /// <param name="rootModel">IRootModel</param>
        /// <param name="linkModel">ILinkModel</param>
        /// <param name="portModel">IPortModel</param>
        public RecordModel(ILogger logger, AppConfig config, AppSettings settings, IRootModel rootModel, ILinkModel linkModel, IPortModel portModel)
        {
            this.logger = logger;
            this.config = config;
            this.rootModel = rootModel;
            this.foloderDialogRequest = new Subject<object>().AddTo(this.CompositeDisposable);
            this.controlLinkLogger = new ControlLinkLogger(logger).AddTo(this.CompositeDisposable);
            this.debugPortTxLogger = new TextPortLogger(logger).AddTo(this.CompositeDisposable);
            this.debugPortRxLogger = new TextPortLogger(logger).AddTo(this.CompositeDisposable);
            this.logPortRxLogger = new TextPortLogger(logger).AddTo(this.CompositeDisposable);

            var recordCurrentData = settings.ToObservableSetting<bool>("RecordCurrentData", true).AddTo(this.CompositeDisposable);
            this.RecordCurrentData = recordCurrentData.ToReactivePropertyAsSynchronized(x => x.Value).AddTo(this.CompositeDisposable);
            var recordHardwareData = settings.ToObservableSetting<bool>("RecordHardwareData", true).AddTo(this.CompositeDisposable);
            this.RecordHardwareData = recordHardwareData.ToReactivePropertyAsSynchronized(x => x.Value).AddTo(this.CompositeDisposable);

            this.hostPortRxLogger = new HostPortLogger(logger, config, this.RecordCurrentData, this.RecordHardwareData, false).AddTo(this.CompositeDisposable);

            this.baseDirectory = settings.ToObservableSetting<string>("BaseRecordDirectory", string.Empty).AddTo(this.CompositeDisposable);
            if (string.IsNullOrEmpty(this.baseDirectory.Value))
            {
                this.baseDirectory.Value = Path.Combine(Directory.GetParent(Assembly.GetEntryAssembly().Location).ToString(), config.DefaultBaseRecordDirectoryName);
            }

            this.BaseDirectory = this.baseDirectory.ToReadOnlyReactivePropertySlim().AddTo(this.CompositeDisposable);
            var chooseDirectory = settings.ToObservableSetting<bool>("ChooseRecordDirectory", false).AddTo(this.CompositeDisposable);
            this.ChooseDirectory = chooseDirectory.ToReactivePropertyAsSynchronized(x => x.Value).AddTo(this.CompositeDisposable);

            linkModel.AppControl.Subscribe(x => this.controlLinkLogger.Write(x, string.Empty)).AddTo(this.CompositeDisposable);
            linkModel.DebugControl.Subscribe(x => this.controlLinkLogger.Write(ControlType.Debug, x)).AddTo(this.CompositeDisposable);
            linkModel.PrintControl.Subscribe(x => this.controlLinkLogger.Write(ControlType.Print, x)).AddTo(this.CompositeDisposable);
            linkModel.HostControl.Subscribe(x => this.controlLinkLogger.Write(ControlType.Host, string.Format("data size = {0} bytes", x.Length - x.Offset))).AddTo(this.CompositeDisposable);

            portModel.DebugPortTransmitted.Subscribe(this.debugPortTxLogger.Write).AddTo(this.CompositeDisposable);
            portModel.DebugPortReceived.Subscribe(this.debugPortRxLogger.Write).AddTo(this.CompositeDisposable);
            portModel.LogPortReceived.Subscribe(this.logPortRxLogger.Write).AddTo(this.CompositeDisposable);
            portModel.HostPortReceived.Subscribe(this.hostPortRxLogger.Write).AddTo(this.CompositeDisposable);
        }

        /// <inheritdoc/>
        public IReadOnlyReactiveProperty<string> BaseDirectory { get; }

        /// <inheritdoc/>
        public IReactiveProperty<bool> ChooseDirectory { get; }

        /// <inheritdoc/>
        public IReactiveProperty<bool> RecordCurrentData { get; }

        /// <inheritdoc/>
        public IReactiveProperty<bool> RecordHardwareData { get; }

        /// <inheritdoc/>
        public IObservable<object> FoloderDialogRequest => this.foloderDialogRequest;

        /// <inheritdoc/>
        public IObservable<HistoryData<ControlType>> ControlLinkMessage => this.controlLinkLogger.Message;

        /// <inheritdoc/>
        public IObservable<HistoryData> DebugPortTxMessage => this.debugPortTxLogger.Message;

        /// <inheritdoc/>
        public IObservable<HistoryData> DebugPortRxMessage => this.debugPortRxLogger.Message;

        /// <inheritdoc/>
        public IObservable<HistoryData> LogPortRxMessage => this.logPortRxLogger.Message;

        /// <inheritdoc/>
        public void Activate()
        {
            var directoryPath = default(string);
            if (this.ChooseDirectory.Value)
            {
                this.foloderDialogRequest.OnNext(null);
                directoryPath = this.setDirectoryCompletion.Task.Result;
            }

            if (directoryPath == null)
            {
                var now = DateTimeOffset.Now;
                directoryPath = Path.Combine(this.baseDirectory.Value, $"{this.config.LogTopDirectoryNamePrefix}{now:yyyyMMdd}_{now:HHmmss}");
            }

            if (IOHelper.CreateDirectory(this.logger, directoryPath)?.Exists != true)
            {
                var message = string.Format("{0}: {1}", Resources.ErrorDialog_MessageWriteLogCreateDirectoryFailure, directoryPath);
                this.rootModel.NotifyErrorDialogRequest(message);
                return;
            }

            this.directoryPath = directoryPath;
            this.logger.Info(string.Format("Record directory created: {0}", directoryPath));
            this.hostPortRxLogger.Activate(directoryPath);

            var failureFiles = new List<string>();
            if (!this.controlLinkLogger.Open(Path.Combine(directoryPath, this.config.ControlLinkLogFileName)))
            {
                failureFiles.Add(this.config.ControlLinkLogFileName);
            }

            if (!this.debugPortTxLogger.Open(Path.Combine(directoryPath, this.config.DebugPortTxLogFileName)))
            {
                failureFiles.Add(this.config.DebugPortTxLogFileName);
            }

            if (!this.debugPortRxLogger.Open(Path.Combine(directoryPath, this.config.DebugPortRxLogFileName)))
            {
                failureFiles.Add(this.config.DebugPortRxLogFileName);
            }

            if (!this.logPortRxLogger.Open(Path.Combine(directoryPath, this.config.LogPortRxLogFileName)))
            {
                failureFiles.Add(this.config.LogPortRxLogFileName);
            }

            if (failureFiles.Count > 0)
            {
                var message = string.Format("{0}: {1}", Resources.ErrorDialog_MessageWriteLogCreateFundamentalFileFailure, string.Join(", ", failureFiles));
                this.rootModel.NotifyErrorDialogRequest(message);
            }
        }

        /// <inheritdoc/>
        public void SetBaseDirectory(string directoryPath)
        {
            this.baseDirectory.Value = directoryPath;
        }

        /// <inheritdoc/>
        public void SetDirectory(string directoryPath)
        {
            this.setDirectoryCompletion.TrySetResult(directoryPath);
        }

        /// <inheritdoc/>
        public void OpenDirectory()
        {
            if (this.directoryPath == null)
            {
                this.logger.Error("Record directory not created.");
                return;
            }

            try
            {
                // エクスプローラーで開くために UseShellExecute = true は必要
                Process.Start(new ProcessStartInfo { FileName = this.directoryPath, UseShellExecute = true });
            }
            catch (Exception e)
            {
                this.logger.Exception("Process.Start", $"FileName = {this.directoryPath}, UseShellExecute = true", e);
                this.logger.Error(string.Format("Unable to open record directory in File Explorer: {0}", this.directoryPath));
            }
        }

        /// <inheritdoc/>
        public void RecordHostPortSnappedRxFrames(IEnumerable<ByteSpan> frames)
        {
            using (var snapLogger = new HostPortLogger(this.logger, this.config, this.RecordCurrentData, this.RecordHardwareData, true))
            {
                snapLogger.Activate(this.directoryPath);
                foreach (var frame in frames)
                {
                    snapLogger.Write(frame);
                }
            }
        }

        private class ControlLinkLogger : FundamentalLoggerBase<HistoryData<ControlType>>
        {
            public ControlLinkLogger(ILogger logger)
                : base(logger)
            {
            }

            public void Write(ControlType type, string message)
            {
                this.Enqueue(() => this.WriteCore(type, message));
            }

            private void WriteCore(ControlType type, string message)
            {
                var data = new HistoryData<ControlType>(type, message);
                var timeText = data.Time.ToString("yyyy-MM-dd HH:mm:ss.ffff");
                var fullText = string.Format("[{0}][{1,-17}] {2}", timeText, type, message);
                this.WriteCore(data, fullText);
            }
        }

        private class TextPortLogger : FundamentalLoggerBase<HistoryData>
        {
            public TextPortLogger(ILogger logger)
                : base(logger)
            {
            }

            public void Write(string message)
            {
                this.Enqueue(() => this.WriteCore(message));
            }

            private void WriteCore(string message)
            {
                var data = new HistoryData(message);
                var timeText = data.Time.ToString("yyyy-MM-dd HH:mm:ss.ffff");
                var fullText = string.Format("[{0}] {1}", timeText, message);
                this.WriteCore(data, fullText);
            }
        }

        private class FundamentalLoggerBase<T> : DisposableBase
        {
            private readonly Subject<T> message = null;
            private readonly ILogger logger = null;
            private StreamWriter streamWriter = null;

            public FundamentalLoggerBase(ILogger logger)
            {
                this.Logger = logger;
                this.Queue = new NonblockingQueue<object>().AddTo(this.CompositeDisposable);  // Dispose() 時にまずキューの受け付けと、残り処理を完了させるため、一番最初に this.CompositeDisposable に追加する。
                this.message = new Subject<T>().AddTo(this.CompositeDisposable);
                Disposable.Create(this.DisposableStreamWriter).AddTo(this.CompositeDisposable);
            }

            private void DisposableStreamWriter()
            {
                this.streamWriter?.Dispose();
                this.streamWriter = null;
            }

            protected ILogger Logger { get; }

            protected NonblockingQueue<object> Queue { get; }

            public IObservable<T> Message => this.message;

            public bool Open(string filePath)
            {
                this.streamWriter = IOHelper.CreateStreamWriter(this.logger, filePath, true);
                if (this.streamWriter == null)
                {
                    this.logger.Error(string.Format("Unable to open file: {0}", filePath));
                    return false;
                }

                return true;
            }

            protected void Enqueue(Action action)
            {
                if (this.streamWriter != null)
                {
                    this.Queue.AddAsync(null, _ => action?.Invoke());
                }
            }

            protected void WriteCore(T message, string fullText, [CallerFilePath] string callerFilePath = "", [CallerLineNumber] int callerLineNumber = -1)
            {
                this.message.OnNext(message);
                IOHelper.WriteLineStream(this.logger, this.streamWriter, fullText, callerFilePath, callerLineNumber);
            }
        }

        private class HostPortLogger : NotifyPropertyChangedBase
        {
            private readonly IReactiveProperty<bool> recordCurrentData = null;
            private readonly IReactiveProperty<bool> recordHardwareData = null;
            private readonly NonblockingQueue<object> queue = null;
            private readonly CurrentDataWriter currentDataWriter = null;
            private readonly HardwareDataWriter hardwareDataWriter = null;
            private readonly bool snap = false;
            private string baseDir = null;
            private bool available = false;

            public HostPortLogger(ILogger logger, AppConfig config, IReactiveProperty<bool> recordCurrentData, IReactiveProperty<bool> recordHardwareData, bool snap)
            {
                this.recordCurrentData = recordCurrentData;
                this.recordHardwareData = recordHardwareData;
                this.snap = snap;
                this.queue = new NonblockingQueue<object>().AddTo(this.CompositeDisposable);    // Dispose() 時にまずキューの受け付けと、残り処理を完了させるため、一番最初に this.CompositeDisposable に追加する。
                this.currentDataWriter = new CurrentDataWriter(logger, config, GetCurrentDataDirectoryPath, GetCurrentDataFilePath, config.FullDataLogMaxFramesPerFile).AddTo(this.CompositeDisposable);
                this.hardwareDataWriter = new HardwareDataWriter(logger, config, GetHardwareDataFilePath, GetHardwareDataHeader(config)).AddTo(this.CompositeDisposable);
            }

            public bool Available
            {
                get => this.available;
                private set => this.SetProperty(ref this.available, value);
            }

            public void Activate(string baseDir)
            {
                this.baseDir = baseDir;
                this.Available = baseDir != null;
            }

            public void Write(ByteSpan frame)
            {
                var dataType = (HostPortDataType)BitConverter.ToUInt16(frame.Array, frame.Offset + 4);  // ペイロード共通データ先頭からオフセット 4 バイト
                if (!dataType.IsBeacon())
                {
                    return;  // 記録しない Host Port Frame Data のため、スキップする。この類の Frame Data は普通に存在するため、アプリログにも残さない。
                }

                if (!this.Available)
                {
                    // RecordModel.Activate() 前もしくは RecordModel.Activate() でディレクトリ作成に失敗した状態のためスキップする。
                    // 大量に記録される可能性があり、RecordModel.Activate() 時にエラーを記録しているため、アプリログにも残さない。
                    return;
                }

                this.queue.AddAsync(null, _ => this.WriteBeaconFrame(dataType, frame));
            }

            private void WriteBeaconFrame(HostPortDataType dataType, ByteSpan frame)
            {
                if (!this.Available)
                {
                    return;
                }

                var serialNumber = BitConverter.ToUInt32(frame.Array, frame.Offset + 0);  // ペイロード共通データ先頭からオフセット 0 バイト
                var bias         = frame.Array[frame.Offset + 8];                         // ペイロード共通データ先頭からオフセット 8 バイト   Bias 電圧設定（単位 0.1V）
                var epPositive   = (sbyte)frame.Array[frame.Offset + 10];                 // ペイロード共通データ先頭からオフセット 10 バイト  +ep 設定（単位 0.1V）
                var epNegative   = (sbyte)frame.Array[frame.Offset + 11];                 // ペイロード共通データ先頭からオフセット 11 バイト  -ep 設定（単位 0.1V）
                var current      = BitConverter.ToInt32(frame.Array, frame.Offset + 12);  // ペイロード共通データ先頭からオフセット 12 バイト  電流値（Raw データ）
                var motor        = BitConverter.ToInt32(frame.Array, frame.Offset + 16);  // ペイロード共通データ先頭からオフセット 16 バイト  ステッピングモーター位置（単位 0.1um）
                var piezo        = BitConverter.ToInt32(frame.Array, frame.Offset + 20);  // ペイロード共通データ先頭からオフセット 20 バイト  ピエゾアクチュエータ位置（単位 1nm）

                // 小数点が "." でない地域などの影響を受けないよう CultureInfo.InvariantCulture を明示
                var time           = (serialNumber / 100.0).ToString("F3", CultureInfo.InvariantCulture);  // 例: 1234.560
                var biasText       = (bias / 10.0).ToString("F1", CultureInfo.InvariantCulture);           // 例: 0.1
                var epPositiveText = (epPositive / 10.0).ToString("F1", CultureInfo.InvariantCulture);     // 例: 1.2
                var epNegativeText = (epNegative / 10.0).ToString("F1", CultureInfo.InvariantCulture);     // 例: -1.2
                var hardwareData   = string.Format("{0},{1},{2},{3},{4},{5},{6},{7},{8}", time, serialNumber, (int)dataType, biasText, current, motor, piezo, epPositiveText, epNegativeText);

                var now = DateTimeOffset.Now;
                if (this.recordHardwareData.Value)
                {
                    this.Available = this.hardwareDataWriter.WriteFrame(this.baseDir, this.snap, now, serialNumber, hardwareData + Environment.NewLine);
                }

                if (this.recordCurrentData.Value)
                {
                    this.Available = this.currentDataWriter.WriteFrame(this.baseDir, this.snap, now, serialNumber, dataType, GetCurrentDataText(hardwareData, frame));
                }
            }

            private static string GetHardwareDataFilePath(AppConfig config, string baseDir, bool snap, DateTimeOffset now)
            {
                var infix = snap ? config.SnapLogNameInfix : string.Empty;
                return Path.Combine(baseDir, $"{config.HardwareLogFileNamePrefix}{infix}{now:yyyyMMdd}_{now:HHmmss}_{now:ffff}{config.HardwareLogFileNameExtension}");
            }

            private static string GetHardwareDataHeader(AppConfig config)
            {
                return string.Format(
                    "{0},{1},{2},{3},{4},{5},{6},{7},{8}{9}",
                    config.HardwareLogColumnHeaderTime,
                    config.HardwareLogColumnHeaderSerialNumber,
                    config.HardwareLogColumnHeaderDataType,
                    config.HardwareLogColumnHeaderBias,
                    config.HardwareLogColumnHeaderCurrent,
                    config.HardwareLogColumnHeaderMotor,
                    config.HardwareLogColumnHeaderPiezo,
                    config.HardwareLogColumnHeaderEpPositive,
                    config.HardwareLogColumnHeaderEpNegative,
                    Environment.NewLine);
            }

            private static string GetCurrentDataDirectoryPath(AppConfig config, string baseDir, bool snap, DateTimeOffset now, HostPortDataType dataType)
            {
                var infix = snap ? config.SnapLogNameInfix : string.Empty;
                var postfix = dataType.IsBeaconCurrentHigh() ? config.FullDataLogDirectoryNamePostfixHighMode : dataType.IsBeaconCurrentLow() ? config.FullDataLogDirectoryNamePostfixLowMode : config.FullDataLogDirectoryNamePostfixNoCurrent;
                var directoryName = $"{config.FullDataLogDirectoryNamePrefix}{infix}{now:yyyyMMdd}_{now:HHmmss}_{now:ffff}{postfix}";
                return Path.Combine(baseDir, directoryName);
            }

            private static string GetCurrentDataFilePath(AppConfig config, string directoryPath, int fileNumber)
            {
                return Path.Combine(directoryPath, $"{config.FullDataLogFileNamePrefix}{fileNumber:D6}{config.FullDataLogFileNameExtension}");
            }

            private static string GetCurrentDataText(string hardwareData, ByteSpan frame)
            {
                var sb = new StringBuilder(16384);   // 符号付32ビット整数 … 1 (符号) + 10 (数字) + 2 (改行) = 最大 13 文字/行。ヘッダも考慮して多めに取る。
                sb.AppendLine("#" + hardwareData);

                var startIndex = frame.Offset + 24;
                var endIndex   = frame.Offset + frame.Length;
                for (var index = startIndex; index < endIndex; index += sizeof(int))
                {
                    var currentN = BitConverter.ToInt32(frame.Array, index);  // ペイロード共通データ先頭からオフセット 24 バイト + 4 x N  電流値 N
                    sb.AppendLine("0x" + currentN.ToString("X8"));
                }

                return sb.ToString();
            }
        }

        private class CurrentDataWriter : BeaconDataWriter
        {
            private readonly AppConfig config = null;
            private readonly Func<AppConfig, string, bool, DateTimeOffset, HostPortDataType, string> getDirectoryPath = null;
            private readonly Func<AppConfig, string, int, string> getFilePath = null;
            private readonly int maxFramesPerFile = default;
            private uint lastSerialNumber = 0xFFFFFFFF;
            private HostPortDataType lastDataType = (HostPortDataType)0xFFFF;

            public CurrentDataWriter(ILogger logger, AppConfig config, Func<AppConfig, string, bool, DateTimeOffset, HostPortDataType, string> getDirectoryPath, Func<AppConfig, string, int, string> getFilePath, int maxFramesPerFile)
                : base(logger, header: null)
            {
                this.config            = config;
                this.getDirectoryPath  = getDirectoryPath;
                this.getFilePath       = getFilePath;
                this.maxFramesPerFile  = maxFramesPerFile;
            }

            public bool WriteFrame(string baseDir, bool snap, DateTimeOffset now, uint serialNumber, HostPortDataType dataType, string text)
            {
                var interrupted = this.lastSerialNumber != serialNumber - 1 || this.lastDataType != dataType;
                if (!this.WriteFrameCore(
                    text: text,
                    skipRequired:            false,                                                          // (1) 電流値列を含まないデータ種別でもスキップしない。
                    rotateDirectoryRequired: interrupted,                                                    // (2) Serial Number またはデータ種別の不連続を検出した場合、新しいディレクトリを作り直して移動する。
                    directoryPath:           this.getDirectoryPath.Invoke(this.config, baseDir, snap, now, dataType),
                    rotateFileRequired:      interrupted || this.FrameCountInFile >= this.maxFramesPerFile,  // (3) 新しいディレクトリに移動した場合、もしくはフレーム数上限に到達した場合、新しいファイルに切り替える。
                    getFilePath:             () => this.getFilePath.Invoke(this.config, this.DirectoryPath, this.FileCountInDirectory)))
                {
                    return false;
                }

                this.lastSerialNumber = serialNumber;
                this.lastDataType     = dataType;
                return true;
            }
        }

        private class HardwareDataWriter : BeaconDataWriter
        {
            private readonly AppConfig config = null;
            private readonly Func<AppConfig, string, bool, DateTimeOffset, string> getFilePath = null;
            private uint lastSerialNumber = 0xFFFFFFFF;

            public HardwareDataWriter(ILogger logger, AppConfig config, Func<AppConfig, string, bool, DateTimeOffset, string> getFilePath, string header)
                : base(logger, header)
            {
                this.config = config;
                this.getFilePath = getFilePath;
            }

            public bool WriteFrame(string baseDir, bool snap, DateTimeOffset now, uint serialNumber, string text)
            {
                if (!this.WriteFrameCore(
                    text:               text,
                    rotateFileRequired: this.lastSerialNumber != serialNumber - 1,  // Serial Number の不連続を検出した場合、新しいファイルに切り替える。
                    getFilePath:        () => this.getFilePath.Invoke(this.config, baseDir, snap, now)))
                {
                    return false;
                }

                this.lastSerialNumber = serialNumber;
                return true;
            }
        }

        private class BeaconDataWriter : DisposableBase
        {
            private readonly ILogger logger = null;
            private readonly string header = null;
            private StreamWriter streamWriter = null;
            private string filePath = null;

            protected BeaconDataWriter(ILogger logger, string header)
            {
                Disposable.Create(this.DisposeStreamWriter).AddTo(this.CompositeDisposable);
                this.logger = logger;
                this.header = header;
            }

            protected void DisposeStreamWriter()
            {
                this.streamWriter?.Dispose();
                this.streamWriter = null;
                this.filePath = null;
                this.FrameCountInFile = 0;
            }

            protected string DirectoryPath { get; private set; } = null;

            protected int FileCountInDirectory { get; private set; } = 0;

            protected int FrameCountInFile { get; private set; } = 0;

            protected bool WriteFrameCore(string text, bool skipRequired = false, bool rotateDirectoryRequired = false, string directoryPath = null, bool rotateFileRequired = false, Func<string> getFilePath = null)
            {
                // (1) 条件を満たす場合、ファイルを閉じてここで正常終了する。
                if (skipRequired)
                {
                    this.DisposeStreamWriter();
                    return true;
                }

                // (2) 条件を満たす場合、新しいディレクトリを作り直して移動する。
                if (rotateDirectoryRequired && directoryPath != null && !this.RotateDirectory(directoryPath))
                {
                    this.logger.Error(string.Format("Unable to rotate log directory: {0}", directoryPath));
                    return false;
                }

                // (3) 条件を満たす場合、新しいファイルに切り替える。
                if (rotateFileRequired && getFilePath != null && !this.RotateFile(getFilePath.Invoke()))
                {
                    this.logger.Error(string.Format("Unable to rotate log file: {0}", getFilePath.Invoke()));
                    return false;
                }

                if (!this.Write(text))
                {
                    this.logger.Error(string.Format("Unable to write text: {0}", text));
                    return false;
                }

                return true;
            }

            private bool RotateDirectory(string directoryPath)
            {
                if (IOHelper.CreateDirectory(this.logger, directoryPath)?.Exists != true)
                {
                    this.logger.Error(string.Format("Unable to create directory: {0}", directoryPath));
                    return false;
                }

                this.DirectoryPath = directoryPath;
                this.FileCountInDirectory = 0;
                return true;
            }

            private bool RotateFile(string filePath)
            {
                this.DisposeStreamWriter();
                this.streamWriter = IOHelper.CreateStreamWriter(this.logger, filePath, false);
                if (this.streamWriter == null)
                {
                    this.logger.Error(string.Format("Unable to create stream writer: {0}", filePath));
                    return false;
                }

                this.filePath = filePath;
                if (this.header != null && !IOHelper.WriteStream(this.logger, this.streamWriter, this.header))
                {
                    this.logger.Error(string.Format("Unable to write header: file path = {0}, header = {1}", filePath, this.header));
                    return false;
                }

                this.FileCountInDirectory++;
                return true;
            }

            private bool Write(string text)
            {
                if (this.streamWriter == null)
                {
                    this.logger.Error(string.Format("File not created: text = {0}", text));
                    return false;
                }

                if (!IOHelper.WriteStream(this.logger, this.streamWriter, text))
                {
                    this.logger.Error(string.Format("Unable to write header: file path = {0}, header = {1}", this.filePath, this.header));
                    return false;
                }

                this.FrameCountInFile++;
                return true;
            }
        }
    }
}
