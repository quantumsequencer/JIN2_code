// Copyright 2026 Sony Global Manufacturing & Operations Corporation

namespace Sony.Jin.Gateway.Views
{
    using System.Windows;
    using Sony.Jin.Gateway.ViewModels;

    /// <summary>
    /// LoopbackWindow.xaml の相互作用ロジック
    /// </summary>
    public partial class LoopbackWindow : Window
    {
        /// <summary>
        /// Initializes a new instance of the <see cref="LoopbackWindow"/> class.
        /// </summary>
        /// <param name="viewModel">LoopbackViewModel</param>
        internal LoopbackWindow(LoopbackViewModel viewModel)
        {
            this.DataContext = viewModel;
            this.InitializeComponent();
        }
    }
}
