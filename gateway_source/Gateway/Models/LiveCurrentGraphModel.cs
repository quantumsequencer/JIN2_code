// Copyright 2026 Sony Global Manufacturing & Operations Corporation

namespace Sony.Jin.Gateway.Models
{
    using System;
    using Reactive.Bindings.Extensions;
    using Sony.Jin.Gateway.Data;
    using Sony.Jin.Shared;

    /// <inheritdoc cref="ILiveCurrentGraphModel"/>
    internal class LiveCurrentGraphModel : CurrentGraphModel, ILiveCurrentGraphModel
    {
        /// <summary>
        /// Initializes a new instance of the <see cref="LiveCurrentGraphModel"/> class.
        /// </summary>
        /// <param name="logger">ILogger</param>
        /// <param name="config">AppConfig</param>
        /// <param name="settings">AppSettings</param>
        /// <param name="portModel">IPortModel</param>
        public LiveCurrentGraphModel(ILogger logger, AppConfig config, AppSettings settings, IPortModel portModel)
            : base(logger, config, settings, null, settingKeyPrefix: "LiveCurrent", snapGraph: false)
        {
            portModel.HostPortReceived.Subscribe(this.ReactHostPortReceived).AddTo(this.CompositeDisposable);
        }

        private void ReactHostPortReceived(ByteSpan data)
        {
            var dataType = (HostPortDataType)BitConverter.ToUInt16(data.Array, data.Offset + 4);  // ペイロード共通データ先頭からオフセット 4 バイト
            int expectedDataBodyLength;
            switch (dataType)
            {
                case HostPortDataType.BeaconNoCurrent:       expectedDataBodyLength = 0; break;
                case HostPortDataType.BeaconCurrentLow10k:   expectedDataBodyLength = sizeof(int) * 100;  break;  // 10ミリ秒当たり 100 サンプル
                case HostPortDataType.BeaconCurrentHigh10k:  expectedDataBodyLength = sizeof(int) * 100;  break;  // 10ミリ秒当たり 100 サンプル
                case HostPortDataType.BeaconCurrentHigh50k:  expectedDataBodyLength = sizeof(int) * 500;  break;  // 10ミリ秒当たり 500 サンプル
                case HostPortDataType.BeaconCurrentHigh100k: expectedDataBodyLength = sizeof(int) * 1000; break;  // 10ミリ秒当たり 1000 サンプル
                default: return;  // 処理すべきではない Host Port Frame Data のため、スキップする。
            }

            var values = new ByteSpan(data.Array, data.Offset + 24, data.Length - 24);  // ペイロード共通データ先頭からオフセット 24 バイト
            if (values.Length != expectedDataBodyLength)
            {
                // 期待される Data Body サイズと異なる。GraphModel のエラーではなく、Port もしくは送信側の問題としてエラーログに記録する。
                this.Logger.Error(string.Format("Wrong data body size detected: data type = {0:X4}h, expected data size = {1}, actual data size = {2}", (ushort)dataType, values.Length, expectedDataBodyLength));
                return;
            }

            var serialNumber = BitConverter.ToUInt32(data.Array, data.Offset + 0);  // ペイロード共通データ先頭からオフセット 0 バイト

            var source = this.GraphSource.Value;
            var newSourceRequired = source == null || source.LastSerialNumber != serialNumber - 1 || source.DataType != dataType;
            this.SetGraphSource(newSourceRequired
                ? new CurrentGraphSource(dataType, serialNumber, values, this.ValueColor, this.MedianColor, this.RmsColor, this.RingBufferCapacity)
                : new CurrentGraphSource(source, serialNumber, values));
        }
    }
}
