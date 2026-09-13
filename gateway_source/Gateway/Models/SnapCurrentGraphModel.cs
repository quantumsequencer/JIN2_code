// Copyright 2026 Sony Global Manufacturing & Operations Corporation

namespace Sony.Jin.Gateway.Models
{
    using Sony.Jin.Gateway.Data;
    using Sony.Jin.Shared;

    /// <inheritdoc cref="ISnapCurrentGraphModel"/>
    internal class SnapCurrentGraphModel : CurrentGraphModel, ISnapCurrentGraphModel
    {
        private readonly IRecordModel recordModel = null;

        /// <summary>
        /// Initializes a new instance of the <see cref="SnapCurrentGraphModel"/> class.
        /// </summary>
        /// <param name="logger">ILogger</param>
        /// <param name="config">AppConfig</param>
        /// <param name="settings">AppSettings</param>
        /// <param name="rootModel">IRootModel</param>
        /// <param name="recordModel">IRecordModel</param>
        public SnapCurrentGraphModel(ILogger logger, AppConfig config, AppSettings settings, IRootModel rootModel, IRecordModel recordModel)
            : base(logger, config, settings, rootModel.NotifySnapCurrentGraphVisibilityRequest, settingKeyPrefix: "SnapCurrent", snapGraph: true)
        {
            this.recordModel = recordModel;
        }

        /// <inheritdoc/>
        public override bool AddGraphSource(CurrentGraphSource graphSource)
        {
            if (graphSource == null)
            {
                this.Logger.Error("Null specified as GraphSource.");
                return false;
            }

            // リングバッファの要素をコピーし、元のリングバッファに追加されても変化しないインスタンスを生成した上で登録する。
            var clonedGraphsource = new CurrentGraphSource(graphSource);
            if (!base.AddGraphSource(clonedGraphsource))
            {
                this.Logger.Error("Failed to add cloned GraphSource.");
                return false;
            }

            this.recordModel.RecordHostPortSnappedRxFrames(clonedGraphsource.GetHostFrames());
            return true;
        }
    }
}
