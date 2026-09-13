// Copyright 2026 Sony Global Manufacturing & Operations Corporation

namespace Sony.Jin.Gateway.Data
{
    using Sony.Jin.Shared;

    /// <summary>
    /// IObservable, INotifyPropertyChanged をサポートする設定（更新可能）
    /// </summary>
    /// <typeparam name="T">値の型</typeparam>
    internal class ObservableSetting<T> : ObservableValue<T>
    {
        /// <summary>
        /// Initializes a new instance of the <see cref="ObservableSetting{T}"/> class.
        /// </summary>
        /// <param name="settings">AppSettings</param>
        /// <param name="keyName">キー名</param>
        /// <param name="initialValue">初期値</param>
        public ObservableSetting(AppSettings settings, string keyName, T initialValue = default)
            : base(
                  getter: (out T v) => settings.GetValue<T>(keyName, out v),
                  setter: v => settings.SetValue<T>(keyName, v),
                  initialValue: initialValue)
        {
        }
    }

    /// <summary>
    /// ObservableSetting の拡張メソッド
    /// </summary>
    [System.Diagnostics.CodeAnalysis.SuppressMessage("StyleCop.CSharp.MaintainabilityRules", "SA1402:File may only contain a single type", Justification = "<保留中>")]
    public static class ObservableSettingExtensions
    {
        /// <summary>
        /// ObservableSetting インスタンスを生成する。
        /// </summary>
        /// <typeparam name="T">値の型</typeparam>
        /// <param name="settings">AppSettings</param>
        /// <param name="keyName">キー名</param>
        /// <param name="initialValue">初期値</param>
        /// <returns>ObservableSetting</returns>
        internal static ObservableSetting<T> ToObservableSetting<T>(this AppSettings settings, string keyName, T initialValue = default)
        {
            return new ObservableSetting<T>(settings, keyName, initialValue);
        }
    }
}
