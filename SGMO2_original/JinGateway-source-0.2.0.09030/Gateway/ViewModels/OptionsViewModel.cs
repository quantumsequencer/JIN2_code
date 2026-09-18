// Copyright 2026 Sony Global Manufacturing & Operations Corporation

namespace Sony.Jin.Gateway.ViewModels
{
    using System;
    using System.Threading.Tasks;
    using Reactive.Bindings;
    using Reactive.Bindings.Extensions;
    using Sony.Jin.Gateway.Models;
    using Sony.Jin.Presentation;
    using Sony.Jin.Shared;

    // INotifyPropertyChanged が実装されていない ViewModel はメモリリークする問題があるため、
    // ViewModel は INotifyPropertyChanged を実装すること（NotifyPropertyChangedBase は実装済み）

    /// <summary>
    /// OptionsViewModel
    /// </summary>
    internal class OptionsViewModel : NotifyPropertyChangedBase
    {
        private readonly IRecordModel recordModel = null;

        /// <summary>
        /// Initializes a new instance of the <see cref="OptionsViewModel"/> class.
        /// </summary>
        /// <param name="rootModel">IRootModel</param>
        /// <param name="recordModel">IRecordModel</param>
        public OptionsViewModel(IRootModel rootModel, IRecordModel recordModel)
        {
            this.recordModel = recordModel;
            this.SetBaseDirectoryCommand = new AsyncReactiveCommand<string>().WithSubscribe(x => Task.Run(() => recordModel.SetBaseDirectory(x)).AddTo(this.CompositeDisposable));

            rootModel.OptionsVisibilityRequest.Subscribe(x => this.Messenger.Raise(MessageVisibilityRequest, x)).AddTo(this.CompositeDisposable);
        }

        /// <summary>
        /// 「ウィンドウの前面表示・非表示要求」のメッセージ名
        /// </summary>
        public const string MessageVisibilityRequest = "VisibilityRequest";

        /// <summary>
        /// Messenger を取得する。
        /// </summary>
        public Messenger Messenger { get; } = new Messenger();

        /// <summary>
        /// 記録ディレクトリの自動作成先を取得する。
        /// </summary>
        public IReadOnlyReactiveProperty<string> BaseDirectory => this.recordModel.BaseDirectory;

        /// <summary>
        /// 記録ディレクトリの起動時選択要否を取得する。
        /// </summary>
        public IReactiveProperty<bool> ChooseDirectory => this.recordModel.ChooseDirectory;

        /// <summary>
        /// 電流測定値の記録要否を取得する。
        /// </summary>
        public IReactiveProperty<bool> RecordCurrentData => this.recordModel.RecordCurrentData;

        /// <summary>
        /// ハードウェア値の記録要否を取得する。
        /// </summary>
        public IReactiveProperty<bool> RecordHardwareData => this.recordModel.RecordHardwareData;

        /// <summary>
        /// 記録ディレクトリの自動作成先を設定するコマンドを取得する。
        /// </summary>
        public AsyncReactiveCommand<string> SetBaseDirectoryCommand { get; }
    }
}
