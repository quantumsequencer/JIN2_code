// Copyright 2026 Sony Global Manufacturing & Operations Corporation

namespace Sony.Jin.Gateway.Models
{
    using System;
    using System.Collections.Generic;
    using System.Collections.ObjectModel;
    using System.Linq;
    using System.Reactive.Disposables;
    using System.Text.RegularExpressions;
    using System.Threading;
    using System.Threading.Tasks;
    using Reactive.Bindings;
    using Reactive.Bindings.Extensions;
    using Sony.Jin.Gateway.Data;
    using Sony.Jin.Shared;

    /// <inheritdoc cref="IStubDebugPortModel"/>
    internal class StubDebugPortModel : DisposableBase, IStubDebugPortModel
    {
        private readonly McbjStateManager mcbjStateManager = null;
        private readonly NonblockingQueue<object> queue = null;
        private readonly Tuple<string, Func<string[]>>[] supportedCommands = null;
        private readonly ILogger logger = null;
        private Action<string> debugReceivedCallback = null;

        /// <summary>
        /// Initializes a new instance of the <see cref="StubDebugPortModel"/> class.
        /// </summary>
        /// <param name="logger">ILogger</param>
        /// <param name="config">AppConfig</param>
        /// <param name="settings">AppSettings</param>
        /// <param name="stubLogPortModel">IStubLogPortModel</param>
        public StubDebugPortModel(ILogger logger, AppConfig config, AppSettings settings, IStubLogPortModel stubLogPortModel)
        {
            this.logger = logger;
            this.mcbjStateManager = new McbjStateManager(stubLogPortModel).AddTo(this.CompositeDisposable);
            this.queue = new NonblockingQueue<object>().AddTo(this.CompositeDisposable);

            this.DebugExecutionTimeItems = config.StubDebugExecutionTimeList.Select(x => new Item<int>(x, string.Format("{0} seconds", x / 1000))).ToList().AsReadOnly();
            this.DebugDdEpBiasResult = CreateReactiveSetting<bool>(settings, "DebugDdEpBiasResult", true, this.CompositeDisposable);
            this.DebugDdEpEpResult   = CreateReactiveSetting<bool>(settings, "DebugDdEpEpResult",   true, this.CompositeDisposable);
            this.DebugMwAcGo0Result  = CreateReactiveSetting<bool>(settings, "DebugMwAcGo0Result",  true, this.CompositeDisposable);
            this.SelectedDebugMcbjSetResultCodeItem           = CreateReactiveSetting<sbyte>(settings, "DebugMcbjSetResultCode",           (sbyte)FWResultCode.SUCCESS, this.DebugResultCodeItems, this.DebugResultCodeItems[0], this.CompositeDisposable);
            this.SelectedDebugAszSetResultCodeItem            = CreateReactiveSetting<sbyte>(settings, "DebugAszSetResultCode",            (sbyte)FWResultCode.SUCCESS, this.DebugResultCodeItems, this.DebugResultCodeItems[0], this.CompositeDisposable);
            this.SelectedDebugSvInfoSenderStartResultCodeItem = CreateReactiveSetting<sbyte>(settings, "DebugSvInfoSenderStartResultCode", (sbyte)FWResultCode.SUCCESS, this.DebugResultCodeItems, this.DebugResultCodeItems[0], this.CompositeDisposable);
            this.SelectedDebugSvInfoSenderStopResultCodeItem  = CreateReactiveSetting<sbyte>(settings, "DebugSvInfoSenderStopResultCode",  (sbyte)FWResultCode.SUCCESS, this.DebugResultCodeItems, this.DebugResultCodeItems[0], this.CompositeDisposable);
            this.SelectedDebugMcbjSubcommandTimeItem = CreateReactiveSetting<int>(settings, "DebugMcbjSubcommandTime", this.DebugExecutionTimeItems[0].Value, this.DebugExecutionTimeItems, this.DebugExecutionTimeItems[0], this.CompositeDisposable);

            var emptyResponse = Array.Empty<string>();
            this.supportedCommands = new Tuple<string, Func<string[]>>[]
            {
                new Tuple<string, Func<string[]>>("dd_ep bias",           () => this.DebugDdEpBiasResult.Value ? new string[] { config.StubDebugDdEpBiasResponseOnSuccess } : emptyResponse),
                new Tuple<string, Func<string[]>>("dd_ep ep",             () => this.DebugDdEpEpResult.Value   ? new string[] { config.StubDebugDdEpEpResponseOnSuccess   } : emptyResponse),
                new Tuple<string, Func<string[]>>("mw_ac go0",            () => this.DebugMwAcGo0Result.Value  ? new string[] { config.StubDebugMwAcGo0ResponseOnSuccess  } : emptyResponse),
                new Tuple<string, Func<string[]>>("sv_info_sender start", () => new string[] { string.Format("{0}{1}", config.StubDebugSvInfoSenderStartResponseHeader, this.SelectedDebugSvInfoSenderStartResultCodeItem.Value.Value) }),
                new Tuple<string, Func<string[]>>("sv_info_sender stop",  () => new string[] { string.Format("{0}{1}", config.StubDebugSvInfoSenderStopResponseHeader,  this.SelectedDebugSvInfoSenderStopResultCodeItem.Value.Value) }),
                new Tuple<string, Func<string[]>>("mcbj set",             () => new string[] { string.Format("{0}{1}", config.StubDebugMcbjSetResponseHeader,           this.SelectedDebugMcbjSetResultCodeItem.Value.Value) }),
                new Tuple<string, Func<string[]>>("asz set",              () => new string[] { string.Format("{0}{1}", config.StubDebugAszSetResponseHeader,            this.SelectedDebugAszSetResultCodeItem.Value.Value) }),
                new Tuple<string, Func<string[]>>("mcbj stop",            () => this.mcbjStateManager.Stop(config.StubDebugMcbjStopResponseOnError)),
                new Tuple<string, Func<string[]>>("mcbj fc start",        () => this.mcbjStateManager.Start(false,  this.SelectedDebugMcbjSubcommandTimeItem.Value.Value, config.StubDebugMcbjFcStartResponseHeaderOnError,        config.StubDebugMcbjFcLogMessageOnCompleted,        config.StubDebugMcbjFcLogMessageOnCanceled)),
                new Tuple<string, Func<string[]>>("mcbj targeting start", () => this.mcbjStateManager.Start(false,  this.SelectedDebugMcbjSubcommandTimeItem.Value.Value, config.StubDebugMcbjTargetingStartResponseHeaderOnError, config.StubDebugMcbjTargetingLogMessageOnCompleted, config.StubDebugMcbjTargetingLogMessageOnCanceled)),
                new Tuple<string, Func<string[]>>("mcbj mt start",        () => this.mcbjStateManager.Start(false,  this.SelectedDebugMcbjSubcommandTimeItem.Value.Value, config.StubDebugMcbjMtStartResponseHeaderOnError,        config.StubDebugMcbjMtLogMessageOnCompleted,        config.StubDebugMcbjMtLogMessageOnCanceled)),
                new Tuple<string, Func<string[]>>("mcbj pt start",        () => this.mcbjStateManager.Start(false,  this.SelectedDebugMcbjSubcommandTimeItem.Value.Value, config.StubDebugMcbjPtStartResponseHeaderOnError,        config.StubDebugMcbjPtLogMessageOnCompleted,        config.StubDebugMcbjPtLogMessageOnCanceled)),
                new Tuple<string, Func<string[]>>("mcbj ac start",        () => this.mcbjStateManager.Start(false,  this.SelectedDebugMcbjSubcommandTimeItem.Value.Value, config.StubDebugMcbjAcStartResponseHeaderOnError,        config.StubDebugMcbjAcLogMessageOnCompleted,        config.StubDebugMcbjAcLogMessageOnCanceled)),
                new Tuple<string, Func<string[]>>("mcbj cal start",       () => this.mcbjStateManager.Start(false,  this.SelectedDebugMcbjSubcommandTimeItem.Value.Value, config.StubDebugMcbjCalStartResponseHeaderOnError,       config.StubDebugMcbjCalLogMessageOnCompleted,       config.StubDebugMcbjCalLogMessageOnCanceled)),
                new Tuple<string, Func<string[]>>("asz eg start",         () => this.mcbjStateManager.Start(false,  this.SelectedDebugMcbjSubcommandTimeItem.Value.Value, config.StubDebugAszEgStartResponseHeaderOnError,         config.StubDebugAszEgLogMessageOnCompleted,         config.StubDebugAszEgLogMessageOnCanceled)),
                new Tuple<string, Func<string[]>>("asz hg start",         () => this.mcbjStateManager.Start(true,   -1,                                                   config.StubDebugAszHgStartResponseHeaderOnError,         config.StubDebugAszHgLogMessageOnCompleted,         config.StubDebugAszHgLogMessageOnCanceled)),
            };
        }

        private static IReactiveProperty<T> CreateReactiveSetting<T>(AppSettings settings, string keyName, T initialSettingValue, CompositeDisposable compositeDisposable)
        {
            var selectedDebugMcbjSubcommandTime = settings.ToObservableSetting<T>(keyName, initialSettingValue).AddTo(compositeDisposable);
            return selectedDebugMcbjSubcommandTime.ToReactivePropertySlimAsSynchronized(x => x.Value).AddTo(compositeDisposable);
        }

        private static IReactiveProperty<Item<T>> CreateReactiveSetting<T>(AppSettings settings, string keyName, T initialSettingValue, IEnumerable<Item<T>> itemCollection, Item<T> defaultPropertyValue, CompositeDisposable compositeDisposable)
        {
            var selectedDebugMcbjSubcommandTime = settings.ToObservableSetting<T>(keyName, initialSettingValue).AddTo(compositeDisposable);
            return selectedDebugMcbjSubcommandTime.ToReactivePropertySlimAsSynchronized(
                x => x.Value,
                x => itemCollection.FirstOrDefault(i => Equals(i.Value, x)) ?? defaultPropertyValue,
                x => x.Value).AddTo(compositeDisposable);
        }

        private static ReadOnlyCollection<Item<sbyte>> CreateResultCodeItems()
        {
            var resultCodeItems = new List<Item<sbyte>>();
            foreach (FWResultCode value in Enum.GetValues(typeof(FWResultCode)))
            {
                resultCodeItems.Add(new Item<sbyte>((sbyte)value, string.Format("{0} ({1})", Enum.GetName(typeof(FWResultCode), value), (sbyte)value)));
            }

            resultCodeItems.Sort((x, y) => y.Value - x.Value);
            return resultCodeItems.AsReadOnly();
        }

        /// <inheritdoc/>
        public ReadOnlyCollection<Item<sbyte>> DebugResultCodeItems { get; } = CreateResultCodeItems();

        /// <inheritdoc/>
        public ReadOnlyCollection<Item<int>> DebugExecutionTimeItems { get; }

        /// <inheritdoc/>
        public IReactiveProperty<bool> DebugDdEpBiasResult { get; }

        /// <inheritdoc/>
        public IReactiveProperty<bool> DebugDdEpEpResult { get; }

        /// <inheritdoc/>
        public IReactiveProperty<bool> DebugMwAcGo0Result { get; }

        /// <inheritdoc/>
        public IReactiveProperty<Item<sbyte>> SelectedDebugSvInfoSenderStartResultCodeItem { get; }

        /// <inheritdoc/>
        public IReactiveProperty<Item<sbyte>> SelectedDebugSvInfoSenderStopResultCodeItem { get; }

        /// <inheritdoc/>
        public IReactiveProperty<Item<sbyte>> SelectedDebugMcbjSetResultCodeItem { get; }

        /// <inheritdoc/>
        public IReactiveProperty<Item<sbyte>> SelectedDebugAszSetResultCodeItem { get; }

        /// <inheritdoc/>
        public IReactiveProperty<Item<int>> SelectedDebugMcbjSubcommandTimeItem { get; }

        /// <inheritdoc/>
        public IReadOnlyReactiveProperty<bool> DebugMcbjRunning => this.mcbjStateManager.Running;

        /// <inheritdoc/>
        public IDisposable DebugSubscribe(Action<string> callback)
        {
            this.debugReceivedCallback += callback ?? throw new ArgumentNullException(nameof(callback));
            return Disposable.Create(() => this.debugReceivedCallback -= callback);
        }

        /// <inheritdoc/>
        public async Task<bool> DebugTransmitAsync(string text)
        {
            // Debug Port の Response は同時には発生しないため、順に1つずつ返すよう Queue で処理する。
            _ = this.queue.AddAsync(null, _ => this.ReturnDebugResponseAsync(text));

            // 送信メソッドのため、Response 通知完了である this.queue.AddAsync() の完了待機はしない。
            return true;
        }

        private async Task ReturnDebugResponseAsync(string command)
        {
            // 間を置いて Response が戻ってきたを模擬し、50 msec 後に非同期で遅らせて行う。
            await Task.Delay(50).ConfigureAwait(false);

            try
            {
                // 照合のため空白文字を詰める。
                command = command?.Trim() ?? string.Empty;
                command = Regex.Replace(command, @"\s+", " ");
                var index = command.IndexOf(' ');
                var firstWord = index != -1 ? command.Substring(0, index) : command;

                if (this.TryGetResponse(command, out var array1))
                {
                    foreach (var line in array1)
                    {
                        this.debugReceivedCallback?.Invoke(line);
                    }
                }
                else if (UsageMessage.Dictionary.TryGetValue(firstWord, out var array2))
                {
                    foreach (var line in array2)
                    {
                        this.debugReceivedCallback?.Invoke(line);
                    }
                }

                this.debugReceivedCallback?.Invoke(string.Empty);
                this.debugReceivedCallback?.Invoke("> ");
            }
            catch (Exception e)
            {
                this.logger.Exception("debugReceivedCallback", "(...)", e);
            }
        }

        private bool TryGetResponse(string command, out string[] response)
        {
            foreach (var itemset in this.supportedCommands)
            {
                if (command.StartsWith(itemset.Item1))
                {
                    response = itemset.Item2.Invoke();
                    return true;
                }
            }

            response = default;
            return false;
        }

        /// <inheritdoc/>
        public Task InsertDebugResponseAsync(string response)
        {
            // Debug Port の Response は同時には発生しないため、順に1つずつ返すよう Queue で処理する。
            return this.queue.AddAsync(null, _ => this.InsertDebugResponse(response));
        }

        private void InsertDebugResponse(string response)
        {
            try
            {
                this.debugReceivedCallback?.Invoke(response);
                this.debugReceivedCallback?.Invoke(string.Empty);
                this.debugReceivedCallback?.Invoke("> ");
            }
            catch (Exception e)
            {
                this.logger.Exception("debugReceivedCallback", $"message = {response}", e);
            }
        }

        /// <inheritdoc/>
        public void RaiseDebugMcbjError() => this.mcbjStateManager.RaiseError();

        private enum FWResultCode : sbyte
        {
            SUCCESS        = 0,    // Success.
            INVALID_HANDLE = -1,   // Invalid handle.
            INVALID_PARAM  = -2,   // Invalid pararameter.
            API_RUNNING    = -3,   // This API is running.
            API_MPF_EMPTY  = -4,   // Memory pool for API is empty.
            API_RUN_FAILED = -5,   // API run failed.
            ALREADY_OPEN   = -6,   // Already opened.
            NOT_OPEN       = -7,   // It is not open.
            CALL_CLOSE     = -8,   // Close API called.
            LOWER_API      = -9,   // Lower API returned error.
            BUFF_OVER      = -10,  // Buffer overflow occurred.
            RECEIVE_ERROR  = -11,  // Receive error occurred.
            WRITE_ERROR    = -12,  // Write error occurred.
            BUS_ERROR      = -13,  // Bus (Peripheral H/W) error.
        }

        private class McbjStateManager : DisposableBase
        {
            private readonly object stateLock = new object();
            private readonly ReactivePropertySlim<bool> running = null;
            private readonly IStubLogPortModel stubLogPortModel = null;
            private CancellationTokenSource externalCauseSource = null;
            private CancellationTokenSource internalCauseSource = null;
            private CancellationTokenSource linkedCauseSource = null;

            public McbjStateManager(IStubLogPortModel stubLogPortModel)
            {
                Disposable.Create(this.DisposeCancellationSource).AddTo(this.CompositeDisposable);

                this.stubLogPortModel = stubLogPortModel;
                this.running = new ReactivePropertySlim<bool>(false).AddTo(this.CompositeDisposable);
                this.Running = this.running.ToReadOnlyReactivePropertySlim().AddTo(this.CompositeDisposable);
            }

            private void DisposeCancellationSource()
            {
                this.linkedCauseSource?.Dispose();
                this.linkedCauseSource = null;
                this.externalCauseSource?.Dispose();
                this.externalCauseSource = null;
                this.internalCauseSource?.Dispose();
                this.internalCauseSource = null;
            }

            public IReadOnlyReactiveProperty<bool> Running { get; }

            public string[] Start(bool stopAsComplete, int millisecondsProcessTime, string responseHeaderOnError, string logMessageOnCompleted, string logMessageOnCanceled)
            {
                lock (this.stateLock)
                {
                    if (this.linkedCauseSource != null)
                    {
                        // ファームウェアの動作に沿って非 IDLE 時は Result Code を API_RUNNING とする。
                        return new string[] { string.Format("{0}{1}", responseHeaderOnError, (sbyte)FWResultCode.API_RUNNING) };
                    }

                    this.running.Value = true;
                    this.externalCauseSource = new CancellationTokenSource();
                    this.internalCauseSource = new CancellationTokenSource();
                    this.linkedCauseSource = CancellationTokenSource.CreateLinkedTokenSource(this.externalCauseSource.Token, this.internalCauseSource.Token);
                    Task.Delay(Math.Max(millisecondsProcessTime, -1), this.linkedCauseSource.Token).ContinueWith(_ =>
                    {
                        var completed = (stopAsComplete || !this.externalCauseSource.IsCancellationRequested) && !this.internalCauseSource.IsCancellationRequested;
                        lock (this.stateLock)
                        {
                            this.DisposeCancellationSource();
                            this.running.Value = false;
                        }

                        _ = this.stubLogPortModel.InsertLogMessageAsync(completed ? logMessageOnCompleted : logMessageOnCanceled);
                    });

                    return new string[] { string.Empty };
                }
            }

            public string[] Stop(string responseHeaderOnError)
            {
                // 制限事項: Stop()/RaiseError() を実行後、Start() の Task 内にある DisposeCancellationSource() が実行される前に、
                //          すぐに Stop()/RaiseError() を実行すると成功に相当する new string[] { string.Empty }; を return する。
                lock (this.stateLock)
                {
                    if (this.externalCauseSource == null)
                    {
                        // ファームウェアの動作に沿って IDLE 時は Result Code を NOT_OPEN とする。
                        return new string[] { string.Format("{0}{1}", responseHeaderOnError, (sbyte)FWResultCode.NOT_OPEN) };
                    }

                    this.externalCauseSource.Cancel();
                    return new string[] { string.Empty };
                }
            }

            public void RaiseError()
            {
                // 制限事項: Stop()/RaiseError() を実行後、Start() の Task 内にある DisposeCancellationSource() が実行される前に、
                //          すぐに Stop()/RaiseError() を実行すると成功に相当する new string[] { string.Empty }; を return する。
                lock (this.stateLock)
                {
                    this.internalCauseSource?.Cancel();
                }
            }
        }

        private static class UsageMessage
        {
            private static readonly ReadOnlyCollection<string> Help = new ReadOnlyCollection<string>(new string[]
            {
                @"pd_flash       : Data Flash Debug.",
                @"pd_gpio        : Set/Get GPIO.",
                @"pd_pwm         : Control PWM.",
                @"bd_i2c         : Read/Write I2C Bus.",
                @"bd_spi         : Read/Write SPI Bus.",
                @"bd_usb         : Tx/Rx USB.",
                @"dd_cur         : Read ADC data.",
                @"dd_ds          : Get Displacement Sensor position.",
                @"dd_ep          : Set Bias/EP.",
                @"dd_motor       : Move motor.",
                @"dd_oc          : Set Offset Compensation.",
                @"dd_piezo       : Move piezo.",
                @"dd_pm          : Set Potentiometer offset.",
                @"dd_temp        : Get Temp.",
                @"md_usb         : md USB test.",
                @"mw_ac          : Actuator Control.",
                @"mw_adj         : Read/Write adjustment data.",
                @"mw_med         : Median calc by ADC data.",
                @"sv_info_sender : Service Info Sender test.",
                @"mcbj           : Do MCBJ func.",
                @"asz            : Do ASZ Mode func.",
                @"top            : Check Performance.",
                @"fw_inf         : Display firmware information.",
                @"fw_ver         : Display firmware version.",
                @"help or ?      : This help.",
            });

            private static readonly ReadOnlyCollection<string> PdFlash = new ReadOnlyCollection<string>(new string[]
            {
                @"pd_flash write data [page_id] 1 [value] : write data flash.",
                @"pd_flash read data [page_id] 1          : read data flash.",
                @"pd_flash blank data [page_id] 1         : blank check data flash.",
                @"pd_flash erase data [block_id] 1        : erase data flash.",
                @" [page_id] : 0 - 3071",
                @" [value]   : 0x00000000 - 0xFFFFFFFF",
                @" [block_id]: 0 - 191",
            });

            private static readonly ReadOnlyCollection<string> PdGpio = new ReadOnlyCollection<string>(new string[]
            {
                @"pd_gpio get [port] [bit]         : Get GPIO.",
                @"pd_gpio set [port] [bit] [value] : Set GPIO.",
                @" [port]  : 0 - 9, A, B.",
                @" [bit]   : 0 - 15.",
                @" [value] : 0(Low), 1(High).",
            });

            private static readonly ReadOnlyCollection<string> PdPwm = new ReadOnlyCollection<string>(new string[]
            {
                @"pd_pwm init                 : Init PWM.",
                @"pd_pwm config [width] [num] : Config PWM.",
                @"pd_pwm start                : Start PWM.",
                @" [width]  : pulse width (us).",
                @" [num]    : pulse num.",
            });

            private static readonly ReadOnlyCollection<string> BdI2c = new ReadOnlyCollection<string>(new string[]
            {
                @"bd_i2c open [Bus No]                                           : Open.",
                @"bd_i2c get [Bus No] [device address] [register address] [size] : Read.",
                @"bd_i2c set [Bus No] [device address] [register address] [data] : Write.",
                @" [Bus No]           : 0, 1.",
                @" [device address]   : 0x00 - 0xFF.",
                @" [register address] : 0x00 - 0xFF.",
                @" [data]             : 0x00 - 0xFF.",
                @" [size]             : read size. (Optional, Max 8)",
            });

            private static readonly ReadOnlyCollection<string> BdSpi = new ReadOnlyCollection<string>(new string[]
            {
                @"bd_spi trans [Bus No] [CS No] [Phase] [Polarity] [data] : Write & Read.",
                @" [Bus No]   : 1. support 1 only.",
                @" [CS No]    : 0 - 3.",
                @" [Phase]    : 0, 1 : 0: odd, 1:even.",
                @" [Polarity] : 0, 1 : 0: Low, 1:High.",
                @" [data]     : e.g. ""1234\xde\xad"".",
            });

            private static readonly ReadOnlyCollection<string> BdUsb = new ReadOnlyCollection<string>(new string[]
            {
                @"bd_usb open [Bus No]      : Open the USB bus driver.",
                @"bd_usb close [Bus No]     : Close the USB bus driver.",
                @"bd_usb rx [Bus No] [size] : Receive.",
                @"bd_usb tx [Bus No] [data] : Send.",
                @" [Bus No]           : 0.",
                @" [data]             : Variable length.Space-separated.",
                @" [size]             : Receive size. (Optional)",
            });

            private static readonly ReadOnlyCollection<string> DdCur = new ReadOnlyCollection<string>(new string[]
            {
                @"dd_cur select [num]         : Select read ADC.",
                @"dd_cur offset               : Get offset setting.",
                @"dd_cur offset [apply]       : Set offset setting.",
                @" [num] :  0 : Low precision  / 10K  speed",
                @"          1 : High precision / 100K speed",
                @"          2 : High precision / 50K  speed",
                @"         10 : High precision / 10K  speed",
                @" [apply] :  on : Enable offset.",
                @"           off : Disable offset.",
            });

            private static readonly ReadOnlyCollection<string> DdDs = new ReadOnlyCollection<string>(new string[]
            {
                @"dd_ds get : Get Displacement Sensor position.",
            });

            private static readonly ReadOnlyCollection<string> DdEp = new ReadOnlyCollection<string>(new string[]
            {
                @"dd_ep bias [bias]         : Set Bias.",
                @"dd_ep unsafebias [usbias] : Set Bias (Unsafe).",
                @"dd_ep ep   [ep]           : Set EP.",
                @"dd_ep abs bias [dec]      : Set Bias by abs dec value.",
                @"dd_ep calib bias [v0] [v1]: Set Bias Calibration data.",
                @" [bias]   : 0 - 2 (divided by 10. 2 means 0.2V).",
                @" [usbias] : 0 - 5 (divided by 10. 5 means 0.5V).",
                @" [ep]     : 0 - 33 (divided by 10. 28 means +2.8 / -2.8V).",
                @" [dec]    : 0 - 65535.",
                @" [v0/v1]  : 0 - 65535. Dec value.v0 must be less than v1.",
            });

            private static readonly ReadOnlyCollection<string> DdMotor = new ReadOnlyCollection<string>(new string[]
            {
                @"dd_motor move [dir] [distance] [speed] : Move motor.",
                @" [dir]      : move direction. CW or CCW.",
                @" [distance] : move distance [um]. (divided by 10. 1 means 0.1 um)",
                @" [speed]    : move speed [um/sec]. (divided by 10. 20 means 2 um/sec)",
            });

            private static readonly ReadOnlyCollection<string> DdOc = new ReadOnlyCollection<string>(new string[]
            {
                @"dd_oc get          : Get Offset Compensation data.",
                @"dd_oc set [dec]    : Set Offset Compensation data.",
                @"dd_oc ioff         : Get Ioff for offset compensation.",
                @"dd_oc calib        : Calibrate Offset Compensation with following parameters",
                @"dd_oc calib [target] [LSB coarse] [LSB fine] [timer] [count]",
                @" [dec]        : 0 - 65535.",
                @" [target]     : 0 - 10 (divided by 10. 5 means ±0.5pA).",
                @" [LSB coarse] : 0 - 255.",
                @" [LSB fine]   : 0 - 255.",
                @" [timer]      : 0 - 1000 (sampling_duration. 100 means 100ms).",
                @" [count]      : 0 - 1200 (max attempts).",
            });

            private static readonly ReadOnlyCollection<string> DdPiezo = new ReadOnlyCollection<string>(new string[]
            {
                @"dd_piezo move [dir] [distance] [speed] : Move Piezo.",
                @"dd_piezo center [speed]                : Go center Piezo.",
                @" [dir]      : move direction. UP or DOWN.",
                @" [distance] : move distance [nm].",
                @" [speed]    : move speed [nm/sec].",
            });

            private static readonly ReadOnlyCollection<string> DdPm = new ReadOnlyCollection<string>(new string[]
            {
                @"dd_pm set [no] [data]      : Set Potentiometer data.",
                @" [no]   : 0, 1  (same as ADC no.).",
                @" [data] : 0 - 1023 (Potentiometer data).",
            });

            private static readonly ReadOnlyCollection<string> DdTemp = new ReadOnlyCollection<string>(new string[]
            {
                @"dd_temp get : Get Temp.",
            });

            private static readonly ReadOnlyCollection<string> MdUsb = new ReadOnlyCollection<string>(new string[]
            {
                @"md_usb test : USB test.",
            });

            private static readonly ReadOnlyCollection<string> MwCc = new ReadOnlyCollection<string>(new string[]
            {
                @"mw_ac go0 : Actuator Control for set 0point.",
                @"mw_ac get [type] : Get Actuator Control Position.",
                @"mw_ac lift [type] [dir] [distance] [speed] : Actuator Control for lift.",
                @" [type]     : lift type. SMOOTH or ROUGH.",
                @" [dir]      : lift direction. UP or DOWN.",
                @" [distance] : lift distance [SMOOTH: nm, ROUGH:um].",
                @" [speed]    : lift speed [SMOOTH: nm/sec, ROUGH:um/sec].",
            });

            private static readonly ReadOnlyCollection<string> MwAdj = new ReadOnlyCollection<string>(new string[]
            {
                @"mw_adj write [type] [data] : Write adjustment data.",
                @"mw_adj read  [type]        : Read adjustment data.",
                @" [type] : 0: Potentiometer0 data, 1: Potentiometer1 data.",
                @"          2: Calibration v0 data, 3: Calibration v1 data.",
                @"          4: Offset Compensation data.",
                @" [data] : 32bit data. (eg. 0x12345678 or 123456789)",
            });

            private static readonly ReadOnlyCollection<string> MwMed = new ReadOnlyCollection<string>(new string[]
            {
                @"mw_med calc [no] : Median calc start.",
                @"mw_med get       : Get Median data.",
                @"mw_med cancel    : Cancel Median calc.",
                @"mw_med fix [data]  : Set the fixed value. (Debug only)",
                @"mw_med cancel_fix  : Cancel the fixed value. (Debug only)",
                @" [no]   : 0  : Low precision  / 10K  speed",
                @"          1  : High precision / 100K speed",
                @"          2  : High precision / 50K  speed",
                @"          10 : High precision / 10K  speed",
                @" [data] : 32bit data. (eg. 0x12345678 or 123456789)",
            });

            private static readonly ReadOnlyCollection<string> SvInfoSender = new ReadOnlyCollection<string>(new string[]
            {
                @"sv_info_sender start [no]  : Info send start.",
                @"sv_info_sender stop        : Info send stop.",
                @"sv_info_sender get         : Get only the latest value.",
                @"sv_info_sender sn_reset    : Reset serial number count.",
                @"sv_info_sender fix [data]  : Set the fixed value. (Debug only)",
                @"sv_info_sender cancel_fix  : Cancel the fixed value. (Debug only)",
                @" [no]   : 0  : Low precision  / 10K  speed",
                @"          1  : High precision / 100K speed",
                @"          2  : High precision / 50K  speed",
                @"          10 : High precision / 10K  speed",
                @" [data] : 32bit data. (eg. 0x12345678 or 123456789)",
            });

            private static readonly ReadOnlyCollection<string> Mcbj = new ReadOnlyCollection<string>(new string[]
            {
                @"mcbj fc start                             : FirstCut start.",
                @"mcbj targeting start                      : Targeting start.",
                @"mcbj mt start                             : MotorTraining start.",
                @"mcbj pt start                             : PiezoTraining start.",
                @"mcbj ac start                             : AutoCut start.",
                @"mcbj cal start                            : Calibration start.",
                @"mcbj stop                                 : MCBJ func stop.",
                @"mcbj set [func] [name] [datas...]         : Setting change.",
            });

            private static readonly ReadOnlyCollection<string> Asz = new ReadOnlyCollection<string>(new string[]
            {
                @"asz eg start                              : ExpandGap start.",
                @"asz hg start                              : HoldGap start.",
                @"asz stop                                  : ASZ Mode func stop.",
                @"asz set [func] [name] [datas...]          : Setting change.",
            });

            private static readonly ReadOnlyCollection<string> Top = new ReadOnlyCollection<string>(new string[]
            {
                @"Performance : 88518",
            });

            private static readonly ReadOnlyCollection<string> FwVer = new ReadOnlyCollection<string>(new string[]
            {
                @"Firmware version : 0.1.6",
            });

            public static readonly ReadOnlyDictionary<string, ReadOnlyCollection<string>> Dictionary = new ReadOnlyDictionary<string, ReadOnlyCollection<string>>(new Dictionary<string, ReadOnlyCollection<string>>()
            {
                { "help", Help },
                { "?", Help },
                { "pd_flash", PdFlash },
                { "pd_gpio", PdGpio },
                { "pd_pwm", PdPwm },
                { "bd_i2c", BdI2c },
                { "bd_spi", BdSpi },
                { "bd_usb", BdUsb },
                { "dd_cur", DdCur },
                { "dd_ds", DdDs },
                { "dd_ep", DdEp },
                { "dd_motor", DdMotor },
                { "dd_oc", DdOc },
                { "dd_piezo", DdPiezo },
                { "dd_pm", DdPm },
                { "dd_temp", DdTemp },
                { "md_usb", MdUsb },
                { "mw_ac", MwCc },
                { "mw_adj", MwAdj },
                { "mw_med", MwMed },
                { "sv_info_sender", SvInfoSender },
                { "mcbj", Mcbj },
                { "asz", Asz },
                { "top", Top },
                { "fw_ver", FwVer },
            });
        }
    }
}
