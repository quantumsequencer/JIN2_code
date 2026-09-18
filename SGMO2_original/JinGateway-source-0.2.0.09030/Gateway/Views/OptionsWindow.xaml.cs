// Copyright 2026 Sony Global Manufacturing & Operations Corporation

namespace Sony.Jin.Gateway.Views
{
    using System.Windows;
    using Sony.Jin.Gateway.ViewModels;

    /// <summary>
    /// OptionsWindow.xaml の相互作用ロジック
    /// </summary>
    public partial class OptionsWindow : Window
    {
        /// <summary>
        /// Initializes a new instance of the <see cref="OptionsWindow"/> class.
        /// </summary>
        /// <param name="viewModel">OptionsViewModel</param>
        internal OptionsWindow(OptionsViewModel viewModel)
        {
            this.DataContext = viewModel;
            this.InitializeComponent();
        }
    }
}
