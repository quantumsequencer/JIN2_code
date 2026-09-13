// Copyright 2026 Sony Global Manufacturing & Operations Corporation

namespace Sony.Jin.Gateway.Models
{
    using System;
    using System.Buffers.Binary;
    using System.Collections.ObjectModel;
    using System.Globalization;
    using System.IO;
    using System.Linq;
    using System.Reactive.Disposables;
    using System.Reactive.Linq;
    using System.Threading.Tasks;
    using Reactive.Bindings;
    using Reactive.Bindings.Extensions;
    using Sony.Jin.Gateway.Data;
    using Sony.Jin.Gateway.Properties;
    using Sony.Jin.Shared;

    /// <inheritdoc cref="IStubHostPortModel"/>
    internal class StubHostPortModel : DisposableBase, IStubHostPortModel
    {
        private const int PayloadCommonPartSize   = 8;   // [0:3] Serial Number [4:5] Data Type [6:7] Reserved
        private const int PayloadBeaconHWDataSize = 16;  // [0] Bias [1] Reserved [2] +ep [3] -ep [4:7] Current [8:11] Motor Position [12:15] Piezo Position
        private readonly object hostStateLock = new object();
        private readonly NonblockingQueue<object> queue = null;
        private readonly ReactivePropertySlim<bool> hostReceiveState = null;
        private readonly ReactivePropertySlim<HostPortFrameSourceType> selectedHostFrameSourceType = null;
        private readonly ReactivePropertySlim<string> hostFullDataLogDirectory = null;
        private readonly ReactivePropertySlim<string> hostHardwareLogFile = null;
        private readonly ReactivePropertySlim<int> hostReceiveCount = null;
        private readonly ILogger logger = null;
        private readonly AppConfig config = null;
        private readonly IRootModel rootModel = null;
        private HighResolutionTimer timer = null;
        private LogReaderBase logReader = null;
        private Action<ByteSpan> hostReceivedCallback = null;
        private int lastCurrentValue = 0;
        private int lastCurrentNValue = 0;
        private int currentNStep = 0;
        private int frameSize = 0;
        private HostPortDataType currentDataType = HostPortDataType.Diag;

        /// <summary>
        /// Initializes a new instance of the <see cref="StubHostPortModel"/> class.
        /// </summary>
        /// <param name="logger">ILogger</param>
        /// <param name="config">AppConfig</param>
        /// <param name="settings">AppSettings</param>
        /// <param name="rootModel">IRootModel</param>
        public StubHostPortModel(ILogger logger, AppConfig config, AppSettings settings, IRootModel rootModel)
        {
            this.logger = logger;
            this.config = config;
            this.rootModel = rootModel;
            this.queue = new NonblockingQueue<object>().AddTo(this.CompositeDisposable);
            this.hostReceiveState = new ReactivePropertySlim<bool>(false).AddTo(this.CompositeDisposable);
            this.HostReceiveState = this.hostReceiveState.ToReadOnlyReactivePropertySlim().AddTo(this.CompositeDisposable);
            this.hostFullDataLogDirectory = new ReactivePropertySlim<string>(null).AddTo(this.CompositeDisposable);
            this.HostFullDataLogDirectory = this.hostFullDataLogDirectory.ToReadOnlyReactivePropertySlim().AddTo(this.CompositeDisposable);
            this.hostHardwareLogFile = new ReactivePropertySlim<string>(null).AddTo(this.CompositeDisposable);
            this.HostHardwareLogFile = this.hostHardwareLogFile.ToReadOnlyReactivePropertySlim().AddTo(this.CompositeDisposable);
            this.hostReceiveCount = new ReactivePropertySlim<int>(0).AddTo(this.CompositeDisposable);
            this.HostReceiveCount = this.hostReceiveCount.ToReadOnlyReactivePropertySlim().AddTo(this.CompositeDisposable);

            var selectedHostFrameSourceType = settings.ToObservableSetting<int>("HostFrameSourceType", (int)HostPortFrameSourceType.FrameGenerator).AddTo(this.CompositeDisposable);
            this.selectedHostFrameSourceType = selectedHostFrameSourceType.ToReactivePropertySlimAsSynchronized(
                x => x.Value,
                x => (HostPortFrameSourceType)x,
                x => (int)x).AddTo(this.CompositeDisposable);
            this.UseHostFullDataLog = this.selectedHostFrameSourceType.Select(x => x == HostPortFrameSourceType.FullDataLog).ToReadOnlyReactivePropertySlim().AddTo(this.CompositeDisposable);
            this.UseHostHardwareLog = this.selectedHostFrameSourceType.Select(x => x == HostPortFrameSourceType.HardwareLog).ToReadOnlyReactivePropertySlim().AddTo(this.CompositeDisposable);
            this.UseHostFrameGenerator = this.selectedHostFrameSourceType.Select(x => x == HostPortFrameSourceType.FrameGenerator).ToReadOnlyReactivePropertySlim().AddTo(this.CompositeDisposable);

            new ReactivePropertySlim<HostPortFrameSourceType>(default).AddTo(this.CompositeDisposable);

            this.HostSerialNumber = new ReactivePropertySlim<uint>(0).AddTo(this.CompositeDisposable);

            var selectedHostDataType = settings.ToObservableSetting<ushort>("HostDataType", (ushort)HostPortDataType.Diag).AddTo(this.CompositeDisposable);
            this.SelectedHostDataTypeItem = selectedHostDataType.ToReactivePropertySlimAsSynchronized(
                x => x.Value,
                x => this.HostDataTypeItems.FirstOrDefault(i => (ushort)i.Value == x) ?? this.HostDataTypeItems[0],
                x => (ushort)x.Value).AddTo(this.CompositeDisposable);

            this.HostFrameSizeItems = config.StubHostDiagFrameSizeList.Select(x => new Item<int>(x, $"{x} bytes")).ToList().AsReadOnly();
            var selectedHostFrameSize = settings.ToObservableSetting<int>("HostFrameSize", config.StubHostDiagDefaultFrameSize).AddTo(this.CompositeDisposable);
            this.SelectedHostFrameSizeItem = selectedHostFrameSize.ToReactivePropertySlimAsSynchronized(
                x => x.Value,
                x => this.HostFrameSizeItems.FirstOrDefault(i => i.Value == x) ?? this.HostFrameSizeItems[0],
                x => x.Value).AddTo(this.CompositeDisposable);

            this.HostFrameIntervalItems = config.StubHostDiagFrameIntervalList.Select(x => new Item<double>(x, $"{x:F0} msec")).ToList().AsReadOnly();
            var selectedHostFrameInterval = settings.ToObservableSetting<double>("HostFrameInterval", config.StubHostDiagDefaultFrameInterval).AddTo(this.CompositeDisposable);
            this.SelectedHostFrameIntervalItem = selectedHostFrameInterval.ToReactivePropertySlimAsSynchronized(
                x => x.Value,
                x => this.HostFrameIntervalItems.FirstOrDefault(i => i.Value == x) ?? this.HostFrameIntervalItems[0],
                x => x.Value).AddTo(this.CompositeDisposable);
        }

        /// <inheritdoc/>
        public ReadOnlyCollection<Item<HostPortDataType>> HostDataTypeItems { get; } = new ReadOnlyCollection<Item<HostPortDataType>>(new Item<HostPortDataType>[]
        {
            new Item<HostPortDataType>(HostPortDataType.BeaconNoCurrent,       Resources.StubWindow_ItemBeaconNoCurrent),
            new Item<HostPortDataType>(HostPortDataType.BeaconCurrentLow10k,   Resources.StubWindow_ItemBeaconCurrentLow10k),
            new Item<HostPortDataType>(HostPortDataType.BeaconCurrentHigh10k,  Resources.StubWindow_ItemBeaconCurrentHigh10k),
            new Item<HostPortDataType>(HostPortDataType.BeaconCurrentHigh50k,  Resources.StubWindow_ItemBeaconCurrentHigh50k),
            new Item<HostPortDataType>(HostPortDataType.BeaconCurrentHigh100k, Resources.StubWindow_ItemBeaconCurrentHigh100k),
            new Item<HostPortDataType>(HostPortDataType.Diag,                  Resources.StubWindow_ItemDiag),
        });

        /// <inheritdoc/>
        public ReadOnlyCollection<Item<int>> HostFrameSizeItems { get; }

        /// <inheritdoc/>
        public ReadOnlyCollection<Item<double>> HostFrameIntervalItems { get; }

        /// <inheritdoc/>
        public IReactiveProperty<Item<HostPortDataType>> SelectedHostDataTypeItem { get; }

        /// <inheritdoc/>
        public IReactiveProperty<Item<int>> SelectedHostFrameSizeItem { get; }

        /// <inheritdoc/>
        public IReactiveProperty<Item<double>> SelectedHostFrameIntervalItem { get; }

        /// <inheritdoc/>
        public IReactiveProperty<uint> HostSerialNumber { get; }

        /// <inheritdoc/>
        public IReadOnlyReactiveProperty<bool> HostReceiveState { get; }

        /// <inheritdoc/>
        public IReadOnlyReactiveProperty<bool> UseHostFullDataLog { get; }

        /// <inheritdoc/>
        public IReadOnlyReactiveProperty<bool> UseHostHardwareLog { get; }

        /// <inheritdoc/>
        public IReadOnlyReactiveProperty<bool> UseHostFrameGenerator { get; }

        /// <inheritdoc/>
        public IReadOnlyReactiveProperty<string> HostFullDataLogDirectory { get; }

        /// <inheritdoc/>
        public IReadOnlyReactiveProperty<string> HostHardwareLogFile { get; }

        /// <inheritdoc/>
        public IReadOnlyReactiveProperty<int> HostReceiveCount { get; }

        /// <inheritdoc/>
        public IDisposable HostSubscribe(Action<ByteSpan> callback)
        {
            this.hostReceivedCallback += callback ?? throw new ArgumentNullException(nameof(callback));
            return Disposable.Create(() => this.hostReceivedCallback -= callback);
        }

        /// <inheritdoc/>
        public async Task<bool> HostTransmitAsync(ByteSpan data)
        {
#if false  // 未実装
            // Host Port の Response は同時には発生しないため、順に1つずつ返すよう Queue で処理する。
            _ = this.queue.AddAsync(null, _ => this.ReturnHostResponseAsync(data));
#endif

            // 送信メソッドのため、Response 通知完了である this.queue.AddAsync() の完了待機はしない。
            return true;
        }

#if false  // 未実装
        private async Task ReturnHostResponseAsync(ByteSpan command)
        {
            // 間を置いて Response が戻ってきたを模擬し、50 msec 後に非同期で遅らせて行う。
            await Task.Delay(50).ConfigureAwait(false);

            try
            {
                // TODO: 必要なコマンドの Stub 動作を実装する。
                this.hostReceivedCallback?.Invoke(response);
            }
            catch (Exception e)
            {
                this.logger.Exception("hostReceivedCallback", "(...)", e);
            }
        }
#endif

        /// <inheritdoc/>
        public void SetHostReceiveState(bool state)
        {
            const long BeaconDueTime = -10 * 10000;  // 10 msec x 1.0e4 … 相対時間の指定のため、負値及び 100 nsec 単位に変換

            lock (this.hostStateLock)
            {
                if (this.hostReceiveState.Value == state)
                {
                    // 現在値と同じ場合は処理をスキップする。
                    return;
                }

                if (state)
                {
                    // 10 kHz = 10000
                    var dueTime = BeaconDueTime;
                    switch (this.selectedHostFrameSourceType.Value)
                    {
                        case HostPortFrameSourceType.FullDataLog:
                            this.logReader = new FullDataLogReader(this.logger, this.config, this.rootModel, this.HostFullDataLogDirectory.Value);
                            this.timer = new HighResolutionTimer(dueTime, this.ReactTimerElapsedFullDataLog);
                            break;

                        case HostPortFrameSourceType.HardwareLog:
                            this.logReader = new HardwareLogReader(this.logger, this.rootModel, this.HostHardwareLogFile.Value);
                            this.timer = new HighResolutionTimer(dueTime, this.ReactTimerElapsedFullDataLog);
                            break;

                        case HostPortFrameSourceType.FrameGenerator:
                            this.currentDataType = this.SelectedHostDataTypeItem.Value.Value;
                            switch (this.currentDataType)
                            {
                                case HostPortDataType.BeaconNoCurrent:       this.currentNStep = 0;                          this.frameSize = PayloadCommonPartSize + PayloadBeaconHWDataSize + (sizeof(int) * 0);    break;
                                case HostPortDataType.BeaconCurrentLow10k:   this.currentNStep = (int)((1U << 31) / 10000);  this.frameSize = PayloadCommonPartSize + PayloadBeaconHWDataSize + (sizeof(int) * 100);  break;
                                case HostPortDataType.BeaconCurrentHigh10k:  this.currentNStep = (int)((1U << 31) / 10000);  this.frameSize = PayloadCommonPartSize + PayloadBeaconHWDataSize + (sizeof(int) * 100);  break;
                                case HostPortDataType.BeaconCurrentHigh50k:  this.currentNStep = (int)((1U << 31) / 50000);  this.frameSize = PayloadCommonPartSize + PayloadBeaconHWDataSize + (sizeof(int) * 500);  break;
                                case HostPortDataType.BeaconCurrentHigh100k: this.currentNStep = (int)((1U << 31) / 100000); this.frameSize = PayloadCommonPartSize + PayloadBeaconHWDataSize + (sizeof(int) * 1000); break;
                                case HostPortDataType.Diag:
                                    this.frameSize = this.SelectedHostFrameSizeItem.Value.Value;
                                    dueTime = -(long)(this.SelectedHostFrameIntervalItem.Value.Value * 1.0e+4);  // 相対時間の指定のため、負値及び 100 nsec 単位に変換する。
                                    break;
                                default:
                                    this.frameSize = 0;
                                    return;
                            }

                            this.lastCurrentNValue = 0;
                            this.timer = new HighResolutionTimer(dueTime, this.ReactTimerElapsedArtificialData);
                            break;

                        default:
                            return;
                    }
                }
                else
                {
                    this.timer?.Dispose();
                    this.timer = null;
                    this.logReader?.Dispose();
                    this.logReader = null;
                }

                this.hostReceiveState.Value = state;
            }
        }

        private void ReactTimerElapsedFullDataLog()
        {
            if (!this.logReader.GetNextFrame(out var frame))
            {
                // SetHostReceiveState(false) で呼び出される HighResolutionTimer.Dispose() でこのメソッド ReactTimerElapsedFullDataLog() の完了待ちをしており、
                // デッドロックを避けるため非同期で呼び出す。
                Task.Run(() => this.SetHostReceiveState(false));
                return;
            }

            // Host Port の Response は同時には発生しないため、順に1つずつ返すよう Queue で処理する。
            _ = this.queue.AddAsync(null, _ => this.NotifyHostResponse(frame));

            this.hostReceiveCount.Value++;
        }

        private void ReactTimerElapsedArtificialData()
        {
            // シリアル通信データヘッダ（8バイト）は含まない。
            var buffer = new byte[this.frameSize];

            // ペイロード共通データ（8バイト）
            var serialNumber = this.HostSerialNumber.Value + 1;
            this.HostSerialNumber.Value = serialNumber;
            BinaryPrimitives.WriteUInt32LittleEndian(buffer.AsSpan(0), serialNumber);                  // [0:3] バイト: Serial Number
            BinaryPrimitives.WriteUInt16LittleEndian(buffer.AsSpan(4), (ushort)this.currentDataType);  // [4:5] バイト: Data Type
            BinaryPrimitives.WriteUInt16LittleEndian(buffer.AsSpan(6), 0);                             // [6:7] バイト: Reserved

            if (this.currentDataType != HostPortDataType.Diag)
            {
                // ペイロード個別データ（ビーコン: ハードウェアデータ 16バイト）
                buffer[PayloadCommonPartSize + 0] = 1;  // [0] Bias
                buffer[PayloadCommonPartSize + 1] = 0;  // [1] Reserved
                buffer[PayloadCommonPartSize + 2] = 0;  // [2] +ep
                buffer[PayloadCommonPartSize + 3] = 0;  // [3] -ep

                this.lastCurrentValue += (int)((1U << 31) / 100);
                if (this.lastCurrentValue < 0)
                {
                    this.lastCurrentValue = 0;
                }

                var motorPosition = (int)(1234 + (serialNumber % 777));
                var piezoPosition = (int)(23456 + ((serialNumber * 8) % 8888));

                BinaryPrimitives.WriteInt32LittleEndian(buffer.AsSpan(PayloadCommonPartSize + 4), this.lastCurrentValue);  // [4:7]   バイト: Current
                BinaryPrimitives.WriteInt32LittleEndian(buffer.AsSpan(PayloadCommonPartSize + 8), motorPosition);          // [8:11]  バイト: Motor Position
                BinaryPrimitives.WriteInt32LittleEndian(buffer.AsSpan(PayloadCommonPartSize + 12), piezoPosition);         // [12:15] バイト: Piezo Position

                // ペイロード個別データ（ビーコン: 電流計測値 400/2000/4000 バイト）
                for (var index = PayloadCommonPartSize + PayloadBeaconHWDataSize; index < buffer.Length; index += 4)
                {
                    this.lastCurrentNValue += this.currentNStep;
                    if (this.lastCurrentNValue < 0)
                    {
                        this.lastCurrentNValue = 0;
                    }

                    BinaryPrimitives.WriteInt32LittleEndian(buffer.AsSpan(index), this.lastCurrentNValue);  // [16:415/2015/4015] バイト: CurrentN
                }
            }

            // Host Port の Response は同時には発生しないため、順に1つずつ返すよう Queue で処理する。
            _ = this.queue.AddAsync(null, _ => this.NotifyHostResponse(new ByteSpan(buffer)));

            this.hostReceiveCount.Value++;
        }

        private void NotifyHostResponse(ByteSpan frame)
        {
            try
            {
                this.hostReceivedCallback?.Invoke(frame);
            }
            catch (Exception e)
            {
                this.logger.Exception("hostReceivedCallback", "frame = (...)", e);
            }
        }

        /// <inheritdoc/>
        public bool SetHostFrameSource(HostPortFrameSourceType sourceType)
        {
            if (!Enum.IsDefined(typeof(HostPortFrameSourceType), sourceType))
            {
                this.logger.Error(string.Format("Undefined value specified as frame source type: {0}", sourceType));
                return false;
            }

            this.selectedHostFrameSourceType.Value = sourceType;
            return true;
        }

        /// <inheritdoc/>
        public bool SetHostFullDataLogDirectory(string directoryPath)
        {
            if (directoryPath == null)
            {
                this.logger.Error("Null specified as directory path.");
                return false;
            }

            this.hostFullDataLogDirectory.Value = directoryPath;
            return true;
        }

        /// <inheritdoc/>
        public bool SetHostHardwareLogFile(string filePath)
        {
            if (filePath == null)
            {
                this.logger.Error("Null specified as file path.");
                return false;
            }

            this.hostHardwareLogFile.Value = filePath;
            return true;
        }

        /// <inheritdoc/>
        public void ResetHostReceiveCount()
        {
            this.hostReceiveCount.Value = 0;
        }

        private class FullDataLogReader : LogReaderBase
        {
            private readonly string[] files = null;
            private int fileIndex = 0;
            private StreamReader streamReader = null;
            private int lineIndex = 0;

            public FullDataLogReader(ILogger logger, AppConfig config, IRootModel rootModel, string directoryPath)
                : base(logger, rootModel)
            {
                Disposable.Create(this.DisposeStreamReader).AddTo(this.CompositeDisposable);

                var searchPattern = $"{config.FullDataLogFileNamePrefix}*{config.FullDataLogFileNameExtension}";
                this.files = Directory.Exists(directoryPath) ? IOHelper.GetFiles(logger, directoryPath, searchPattern)?.OrderBy(x => x).ToArray() ?? Array.Empty<string>() : Array.Empty<string>();
            }

            private void DisposeStreamReader()
            {
                this.streamReader?.Dispose();
                this.streamReader = null;
            }

            /// <remarks>
            /// 戻値はエラーの有無ではなく、Frame Data を返すことが出来たかを示す。
            /// それには正常にファイルすべてを読み終えた場合とファイルオープンエラー、読み出しエラー、行のパースエラーによる場合があるため、エラーログ出力及びエラーダイアログ表示はメソッド内で行う。
            /// </remarks>
            protected override bool GetNextFrameCore(out ByteSpan frame)
            {
                frame = default;

                if (!this.ReadFrameHeader(out var header))
                {
                    // ディレクトリ内のファイルすべての処理を完了して return false する場合があるため、ここにエラーメッセージ処理は置かない。
                    return false;
                }

                if (!header.StartsWith("#") || !TryParseHardwareDataLine(header.Substring(1), out var serialNumber, out var dataType, out var bias, out var current, out var motorPosition, out var piezoPosition, out var epPositive, out var epNegative, out var frameSize))
                {
                    var message = string.Format("{0}: {1}, line {2}", Resources.ErrorDialog_MessageReadLogInvalidFrameHeader, this.files[this.fileIndex - 1], this.lineIndex);
                    this.RootModel.NotifyErrorDialogRequest(message);
                    return false;
                }

                var buffer = new byte[frameSize];

                // ペイロード共通データ（8バイト）+ ペイロード個別データ（ビーコン: ハードウェアデータ 16バイト）
                WritePayloadBeaconData(buffer, serialNumber, dataType, bias, current, motorPosition, piezoPosition, epPositive, epNegative);

                // ペイロード個別データ（ビーコン: 電流計測値 400/2000/4000 バイト）
                for (var index = PayloadCommonPartSize + PayloadBeaconHWDataSize; index < buffer.Length; index += 4)
                {
                    var line = IOHelper.ReadLine(this.Logger, this.streamReader);
                    this.lineIndex++;

                    if (!TryParseCurrentN(line, out var currentN))
                    {
                        var message = string.Format("{0}: {1}, line {2}", Resources.ErrorDialog_MessageReadLogInvalidCurrentValue, this.files[this.fileIndex - 1], this.lineIndex);
                        this.RootModel.NotifyErrorDialogRequest(message);
                        return false;
                    }

                    BinaryPrimitives.WriteInt32LittleEndian(buffer.AsSpan(index), currentN);  // [16:415/2015/4015] バイト: CurrentN
                }

                frame = new ByteSpan(buffer);
                return true;
            }

            /// <remarks>
            /// 戻値はエラーの有無ではなく、次のファイルをオープン出来たかを示す。
            /// それには正常にファイルすべてを読み終えた場合とファイルオープンエラーによる場合があるため、エラーログ出力及びエラーダイアログ表示はメソッド内で行う。
            /// </remarks>
            private bool OpenNextFile()
            {
                if (this.fileIndex >= this.files.Length)
                {
                    // ディレクトリ内のファイルすべての処理を完了したことを意味するのでエラーではない。
                    // 但し、呼び出し元の処理を終了させるため return false する。
                    return false;
                }

                this.streamReader = IOHelper.CreateStreamReader(this.Logger, this.files[this.fileIndex]);
                if (this.streamReader == null)
                {
                    var message = string.Format("{0}: {1}", Resources.ErrorDialog_MessageReadLogOpenFileFailure, this.files[this.fileIndex]);
                    this.RootModel.NotifyErrorDialogRequest(message);
                    return false;
                }

                this.fileIndex++;
                this.lineIndex = 0;
                return true;
            }

            /// <remarks>
            /// 戻値はエラーの有無ではなく、ヘッダ行を返すことが出来たかを示す。
            /// それには正常にファイルすべてを読み終えた場合と読み出しのエラーによる場合があるため、エラーログ出力及びエラーダイアログ表示はメソッド内で行う。
            /// </remarks>
            private bool ReadFrameHeader(out string header)
            {
                header = default;
                if (this.streamReader == null)
                {
                    if (!this.OpenNextFile())
                    {
                        // ディレクトリ内のファイルすべての処理を完了して return false する場合があるため、ここにエラーメッセージ処理は置かない。
                        return false;
                    }
                }

                if (!TryReadLine(this.Logger, this.streamReader, out header))
                {
                    // ファイル終端の場合を考慮し、次のファイルをオープンして再度 ReadLine() を実行する。
                    this.DisposeStreamReader();
                    if (!this.OpenNextFile())
                    {
                        // ディレクトリ内のファイルすべての処理を完了して return false する場合があるため、ここにエラーメッセージ処理は置かない。
                        return false;
                    }

                    if (!TryReadLine(this.Logger, this.streamReader, out header))
                    {
                        var message = string.Format("{0}: {1}, line {2}", Resources.ErrorDialog_MessageReadLogReadLineFailure, this.files[this.fileIndex - 1], this.lineIndex + 1);
                        this.RootModel.NotifyErrorDialogRequest(message);
                        return false;
                    }
                }

                this.lineIndex++;
                return true;
            }

            private static bool TryParseCurrentN(string line, out int currentN)
            {
                currentN = default;

                if (line == null) return false;
                if (!line.StartsWith("0x")) return false;
                if (!int.TryParse(line.Substring(2), NumberStyles.HexNumber, null, out currentN)) return false;

                return true;
            }
        }

        private class HardwareLogReader : LogReaderBase
        {
            private readonly StreamReader streamReader = null;
            private readonly string filePath = null;
            private int lineIndex = 0;

            public HardwareLogReader(ILogger logger, IRootModel rootModel, string filePath)
                : base(logger, rootModel)
            {
                if (string.IsNullOrEmpty(filePath))
                {
                    // 未入力の場合、エラーメッセージ処理は行わない。
                    return;
                }

                this.streamReader = OpenFile(logger, rootModel, filePath, out var lineIndex)?.AddTo(this.CompositeDisposable);
                this.filePath = filePath;
                this.lineIndex = lineIndex;
            }

            /// <remarks>
            /// 戻値はエラーの有無ではなく、Frame Data を返すことが出来たかを示す。
            /// それには正常にファイルすべてを読み終えた場合とファイルオープンエラー、読み出しエラー、行のパースエラーによる場合があるため、エラーログ出力及びエラーダイアログ表示はメソッド内で行う。
            /// </remarks>
            protected override bool GetNextFrameCore(out ByteSpan frame)
            {
                frame = default;

                if (!this.ReadHardwareDataLine(out var line))
                {
                    // 正常にファイルすべてを読み終えて return false する場合があるため、ここにエラーメッセージ処理は置かない。
                    return false;
                }

                if (!TryParseHardwareDataLine(line, out var serialNumber, out var _, out var bias, out var current, out var motorPosition, out var piezoPosition, out var epPositive, out var epNegative, out _))
                {
                    var message = string.Format("{0}: {1}, line {2}", Resources.ErrorDialog_MessageReadLogInvalidHardwareData, this.filePath, this.lineIndex);
                    this.RootModel.NotifyErrorDialogRequest(message);
                    return false;
                }

                // ペイロード共通データ（8バイト）+ ペイロード個別データ（ビーコン: ハードウェアデータ 16バイト）
                var buffer = new byte[PayloadCommonPartSize + PayloadBeaconHWDataSize];
                WritePayloadBeaconData(buffer, serialNumber, (ushort)HostPortDataType.BeaconNoCurrent, bias, current, motorPosition, piezoPosition, epPositive, epNegative);
                frame = new ByteSpan(buffer);
                return true;
            }

            /// <remarks>
            /// 戻値はエラーの有無ではなく、行を返すことが出来たかを示す。
            /// それには正常にファイルすべてを読み終えた場合と読み出しのエラーによる場合があるため、エラーログ出力及びエラーダイアログ表示はメソッド内で行う。
            /// </remarks>
            private bool ReadHardwareDataLine(out string line)
            {
                line = default;
                if (this.streamReader == null)
                {
                    // コンストラクタでエラー処理済みのため、ここにエラーメッセージ処理は置かない。
                    return false;
                }

                if (this.streamReader.EndOfStream)
                {
                    // ファイル終端の場合は正常動作としてヘッダ行が取れなかったことにより return false する。
                    return false;
                }

                if (!TryReadLine(this.Logger, this.streamReader, out line))
                {
                    var message = string.Format("{0}: {1}, line {2}", Resources.ErrorDialog_MessageReadLogReadLineFailure, this.filePath, this.lineIndex + 1);
                    this.RootModel.NotifyErrorDialogRequest(message);
                    return false;
                }

                this.lineIndex++;
                return true;
            }

            private static StreamReader OpenFile(ILogger logger, IRootModel rootModel, string filePath, out int lineIndex)
            {
                lineIndex = 0;

                var streamReader = IOHelper.CreateStreamReader(logger, filePath);
                if (streamReader == null)
                {
                    var message = string.Format("{0}: {1}", Resources.ErrorDialog_MessageReadLogOpenFileFailure, filePath);
                    rootModel.NotifyErrorDialogRequest(message);
                    return null;
                }

                lineIndex++;

                // 補足: ファイル終端の場合、StreamReader.ReadLine() は例外を発生せず return null する。
                if (!TryReadLine(logger, streamReader, out var header))
                {
                    var message = string.Format("{0}: {1}, line {2}", Resources.ErrorDialog_MessageReadLogReadLineFailure, filePath, lineIndex);
                    rootModel.NotifyErrorDialogRequest(message);
                    streamReader.Dispose();
                    return null;
                }

                if (header != "Time,SerialNumber,DataType,Bias,Current,MotorPos,PiezoPos,+ep,-ep")
                {
                    var message = string.Format("{0}: {1}, line {2}", Resources.ErrorDialog_MessageReadLogInvalidHardwareDataHeader, filePath, lineIndex);
                    rootModel.NotifyErrorDialogRequest(message);
                    streamReader.Dispose();
                    return null;
                }

                return streamReader;
            }
        }

        private abstract class LogReaderBase : DisposableBase
        {
            private bool terminated = false;

            protected LogReaderBase(ILogger logger, IRootModel rootModel)
            {
                this.Logger = logger;
                this.RootModel = rootModel;
            }

            protected ILogger Logger { get; }

            protected IRootModel RootModel { get; }

            /// <remarks>
            /// 戻値はエラーの有無ではなく、Frame Data を返すことが出来たかを示す。
            /// それには正常にファイルすべてを読み終えた場合とエラーによる場合があるため、エラーログ出力及びエラーダイアログ表示はメソッド内で行う。
            /// </remarks>
            public bool GetNextFrame(out ByteSpan frame)
            {
                frame = default;

                // 一度 Frame 取得が出来なかったら、以降は GetNextFrameCore() を呼び出さずに return false する。
                // 背景: HighResolutionTimer の停止・破棄の前に再度コールバックが呼び出されることがあり、エラーダイアログが二重に表示されるため。
                if (this.terminated || !this.GetNextFrameCore(out frame))
                {
                    this.terminated = true;
                    return false;
                }

                return true;
            }

            /// <remarks>
            /// 戻値はエラーの有無ではなく、Frame Data を返すことが出来たかを示す。
            /// それには正常にファイルすべてを読み終えた場合とファイルオープンエラー、読み出しエラー、行のパースエラーによる場合があるため、エラーログ出力及びエラーダイアログ表示はメソッド内で行う。
            /// </remarks>
            protected abstract bool GetNextFrameCore(out ByteSpan frame);

            protected static bool TryParseHardwareDataLine(string line, out uint serialNumber, out ushort dataType, out double bias, out int current, out int motorPosition, out int piezoPosition, out double epPositive, out double epNegative, out int frameSize)
            {
                serialNumber  = default;
                dataType      = default;
                bias          = default;
                current       = default;
                motorPosition = default;
                piezoPosition = default;
                epPositive    = default;
                epNegative    = default;
                frameSize     = default;

                // ヘッダ行  例: 12.450,1,4,0.1,21474836,1235,23464,0.0,0.0
                var items = line.Split(',');
                if (items.Length != 9)
                {
                    return false;
                }

                if (!uint.TryParse(items[1],   out serialNumber))  return false;
                if (!ushort.TryParse(items[2], out dataType))      return false;
                if (!double.TryParse(items[3], out bias))          return false;
                if (!int.TryParse(items[4],    out current))       return false;
                if (!int.TryParse(items[5],    out motorPosition)) return false;
                if (!int.TryParse(items[6],    out piezoPosition)) return false;
                if (!double.TryParse(items[7], out epPositive))    return false;
                if (!double.TryParse(items[8], out epNegative))    return false;

                switch ((HostPortDataType)dataType)
                {
                    case HostPortDataType.BeaconNoCurrent:       frameSize = PayloadCommonPartSize + PayloadBeaconHWDataSize + (sizeof(int) * 0);    break;
                    case HostPortDataType.BeaconCurrentLow10k:   frameSize = PayloadCommonPartSize + PayloadBeaconHWDataSize + (sizeof(int) * 100);  break;
                    case HostPortDataType.BeaconCurrentHigh10k:  frameSize = PayloadCommonPartSize + PayloadBeaconHWDataSize + (sizeof(int) * 100);  break;
                    case HostPortDataType.BeaconCurrentHigh50k:  frameSize = PayloadCommonPartSize + PayloadBeaconHWDataSize + (sizeof(int) * 500);  break;
                    case HostPortDataType.BeaconCurrentHigh100k: frameSize = PayloadCommonPartSize + PayloadBeaconHWDataSize + (sizeof(int) * 1000); break;
                    default: return false;
                }

                return true;
            }

            protected static void WritePayloadBeaconData(byte[] buffer, uint serialNumber, ushort dataType, double bias, int current, int motorPosition, int piezoPosition, double epPositive, double epNegative)
            {
                // ペイロード共通データ（8バイト）
                BinaryPrimitives.WriteUInt32LittleEndian(buffer.AsSpan(0), serialNumber);  // [0:3] バイト: Serial Number
                BinaryPrimitives.WriteUInt16LittleEndian(buffer.AsSpan(4), dataType);      // [4:5] バイト: Data Type
                BinaryPrimitives.WriteUInt16LittleEndian(buffer.AsSpan(6), 0);             // [6:7] バイト: Reserved

                // ペイロード個別データ（ビーコン: ハードウェアデータ 16バイト）
                buffer[PayloadCommonPartSize + 0] = (byte)(bias * 10);        // [0] Bias
                buffer[PayloadCommonPartSize + 1] = 0;                        // [1] Reserved
                buffer[PayloadCommonPartSize + 2] = (byte)(epPositive * 10);  // [2] +ep
                buffer[PayloadCommonPartSize + 3] = (byte)(epNegative * 10);  // [3] -ep
                BinaryPrimitives.WriteInt32LittleEndian(buffer.AsSpan(PayloadCommonPartSize + 4), current);         // [4:7]   バイト: Current
                BinaryPrimitives.WriteInt32LittleEndian(buffer.AsSpan(PayloadCommonPartSize + 8), motorPosition);   // [8:11]  バイト: Motor Position
                BinaryPrimitives.WriteInt32LittleEndian(buffer.AsSpan(PayloadCommonPartSize + 12), piezoPosition);  // [12:15] バイト: Piezo Position
            }

            protected static bool TryReadLine(ILogger logger, StreamReader streamReader, out string line)
            {
                line = IOHelper.ReadLine(logger, streamReader);
                return line != null;
            }
        }
    }
}
