param([switch]$Preview)

$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName PresentationFramework, PresentationCore, WindowsBase
$root = $PSScriptRoot

[xml]$xaml = @'
<Window xmlns="http://schemas.microsoft.com/winfx/2006/xaml/presentation"
        xmlns:x="http://schemas.microsoft.com/winfx/2006/xaml"
        Title="JIN SAMURAI | スタート" Width="1060" Height="740"
        MinWidth="760" MinHeight="560" WindowStartupLocation="CenterScreen"
        Background="#F5F3EE" FontFamily="Yu Gothic UI" Foreground="#202B3C">
  <Window.Resources>
    <Style TargetType="Button">
      <Setter Property="Cursor" Value="Hand"/>
      <Setter Property="FontSize" Value="18"/>
      <Setter Property="FontWeight" Value="Bold"/>
      <Setter Property="Foreground" Value="White"/>
      <Setter Property="Padding" Value="20,14"/>
      <Setter Property="Template">
        <Setter.Value><ControlTemplate TargetType="Button">
          <Border x:Name="surface" Background="{TemplateBinding Background}" CornerRadius="15"
                  Padding="{TemplateBinding Padding}" BorderBrush="#202B3C" BorderThickness="0">
            <ContentPresenter HorizontalAlignment="Center" VerticalAlignment="Center"/>
          </Border>
          <ControlTemplate.Triggers>
            <Trigger Property="IsMouseOver" Value="True"><Setter TargetName="surface" Property="Opacity" Value="0.82"/></Trigger>
            <Trigger Property="IsKeyboardFocused" Value="True"><Setter TargetName="surface" Property="BorderThickness" Value="3"/></Trigger>
            <Trigger Property="IsEnabled" Value="False"><Setter TargetName="surface" Property="Opacity" Value="0.45"/></Trigger>
          </ControlTemplate.Triggers>
        </ControlTemplate></Setter.Value>
      </Setter>
    </Style>
  </Window.Resources>
  <Viewbox Stretch="Uniform">
    <Grid Width="1000" Height="660" Margin="20">
      <Grid.RowDefinitions><RowDefinition Height="88"/><RowDefinition Height="*"/><RowDefinition Height="58"/></Grid.RowDefinitions>
      <Border Width="54" Height="54" HorizontalAlignment="Left" VerticalAlignment="Top"
              Background="#202B3C" CornerRadius="27" Padding="6">
        <Image x:Name="BrandMark" Stretch="Uniform"
               RenderOptions.BitmapScalingMode="HighQuality" SnapsToDevicePixels="True"/>
      </Border>
      <StackPanel Margin="68,0,0,0">
        <TextBlock Text="JIN / SAMURAI" FontSize="25" FontWeight="Black"/>
        <TextBlock Text="さあ、今日の一歩をはじめよう。" FontSize="15" Margin="0,6,0,0" Foreground="#677285"/>
      </StackPanel>
      <Border HorizontalAlignment="Right" VerticalAlignment="Top" Background="#FFE49A" CornerRadius="18" Padding="18,9">
        <TextBlock Text="WELCOME !" FontWeight="Bold" FontSize="14"/>
      </Border>
      <CheckBox x:Name="MotionEnabled" Content="侍のアニメーション" IsChecked="True"
                HorizontalAlignment="Right" VerticalAlignment="Top" Margin="0,48,0,0" Foreground="#677285"/>
      <Grid Grid.Row="1">
        <Grid.ColumnDefinitions><ColumnDefinition Width="345"/><ColumnDefinition Width="28"/><ColumnDefinition Width="*"/></Grid.ColumnDefinitions>
        <Border Background="#FFE6DE" CornerRadius="28" ClipToBounds="True">
          <Grid>
            <Ellipse Fill="#FFD0BC" Width="305" Height="305" VerticalAlignment="Center"/>
            <TextBlock Text="いざ、出発！" FontSize="31" FontWeight="Black" Margin="26,23,0,0"/>
            <Image x:Name="Samurai" Margin="10,74,10,42" Stretch="Uniform" RenderOptions.BitmapScalingMode="HighQuality">
              <Image.RenderTransform><TranslateTransform x:Name="SamuraiFloat"/></Image.RenderTransform>
            </Image>
            <Border Background="White" CornerRadius="16" Margin="20,0,20,19" Padding="14,11" VerticalAlignment="Bottom">
              <Button x:Name="TalkButton" Background="White" Foreground="#202B3C" Padding="0"
                      FontSize="16" Content="使いたい画面を選んでくれ！" ToolTip="クリックすると侍のひと言が変わります"/>
            </Border>
          </Grid>
        </Border>
        <Grid Grid.Column="2">
          <Grid.RowDefinitions><RowDefinition Height="62"/><RowDefinition Height="*"/><RowDefinition Height="16"/><RowDefinition Height="*"/></Grid.RowDefinitions>
          <StackPanel>
            <TextBlock Text="どちらではじめますか？" FontSize="28" FontWeight="Bold"/>
            <TextBlock Text="目的に合わせて、起動するアプリを選択。" Foreground="#677285" Margin="0,3,0,0" FontSize="14"/>
          </StackPanel>
          <Border Grid.Row="1" Background="#E0F5EE" BorderBrush="#A7DCCB" BorderThickness="1" CornerRadius="22" Padding="23,17">
            <Grid>
              <Grid.RowDefinitions><RowDefinition Height="Auto"/><RowDefinition Height="Auto"/><RowDefinition Height="*"/><RowDefinition Height="Auto"/></Grid.RowDefinitions>
              <TextBlock Text="01  /  USER" Foreground="#247764" FontWeight="Bold" FontSize="13"/>
              <TextBlock Grid.Row="1" Text="ユーザー版" FontSize="29" FontWeight="Bold" Margin="0,3,0,0"/>
              <TextBlock Grid.Row="2" Text="いつもの操作・測定はこちら。" FontSize="15" Margin="0,5,0,8"/>
              <Button x:Name="UserButton" Grid.Row="3" Content="ユーザー版を起動  →" Background="#167D69" AutomationProperties.Name="ユーザー版 demo を起動"/>
            </Grid>
          </Border>
          <Border Grid.Row="3" Background="#EDE8FD" BorderBrush="#D0C3F3" BorderThickness="1" CornerRadius="22" Padding="23,17">
            <Grid>
              <Grid.RowDefinitions><RowDefinition Height="Auto"/><RowDefinition Height="Auto"/><RowDefinition Height="*"/><RowDefinition Height="Auto"/></Grid.RowDefinitions>
              <TextBlock Text="02  /  DEVELOPMENT" Foreground="#7056AB" FontWeight="Bold" FontSize="13"/>
              <TextBlock Grid.Row="1" Text="開発版" FontSize="29" FontWeight="Bold" Margin="0,3,0,0"/>
              <TextBlock Grid.Row="2" Text="機能の開発・動作確認はこちら。" FontSize="15" Margin="0,5,0,8"/>
              <Button x:Name="DevButton" Grid.Row="3" Content="開発版を起動  →" Background="#7859B7" AutomationProperties.Name="開発版 test2 を起動"/>
            </Grid>
          </Border>
        </Grid>
      </Grid>
      <TextBlock x:Name="Status" Grid.Row="2" Text="アプリ起動後、接続・測定は各画面から操作できます。" VerticalAlignment="Center" Foreground="#677285" FontSize="14"/>
      <ProgressBar x:Name="LaunchProgress" Grid.Row="2" Height="4" VerticalAlignment="Bottom"
                   IsIndeterminate="True" Visibility="Collapsed" Foreground="#167D69" BorderThickness="0"/>
    </Grid>
  </Viewbox>
</Window>
'@
$reader = New-Object System.Xml.XmlNodeReader $xaml
$window = [Windows.Markup.XamlReader]::Load($reader)
$markPath = Join-Path $root 'demo\assets\jin_mark_white.png'
if (Test-Path -LiteralPath $markPath) {
    $mark = New-Object Windows.Media.Imaging.BitmapImage ([Uri]$markPath)
    $window.FindName('BrandMark').Source = $mark
    # Draw the white emblem on a dark circle so it reads on light title bars too.
    $visual = New-Object Windows.Media.DrawingVisual
    [Windows.Media.RenderOptions]::SetBitmapScalingMode($visual, [Windows.Media.BitmapScalingMode]::HighQuality)
    $context = $visual.RenderOpen()
    $brush = [Windows.Media.BrushConverter]::new().ConvertFromString('#202B3C')
    $context.DrawEllipse($brush, $null, [Windows.Point]::new(32,32), 32, 32)
    $context.DrawImage($mark, [Windows.Rect]::new(7,7,50,50))
    $context.Close()
    $icon = New-Object Windows.Media.Imaging.RenderTargetBitmap 256, 256, 384, 384, ([Windows.Media.PixelFormats]::Pbgra32)
    $icon.Render($visual)
    $icon.Freeze()
    $window.Icon = $icon
}
$status = $window.FindName('Status')
$userButton = $window.FindName('UserButton')
$devButton = $window.FindName('DevButton')
$portrait = $window.FindName('Samurai')
$talk = $window.FindName('TalkButton')
$motion = $window.FindName('MotionEnabled')
$progress = $window.FindName('LaunchProgress')
$float = $window.FindName('SamuraiFloat')
$script:poses = @()
$atlasPath = Join-Path $root 'demo\assets\samurai_host_atlas.png'
if (Test-Path -LiteralPath $atlasPath) {
    $bitmap = New-Object Windows.Media.Imaging.BitmapImage
    $bitmap.BeginInit()
    $bitmap.CacheOption = [Windows.Media.Imaging.BitmapCacheOption]::OnLoad
    $bitmap.UriSource = [Uri]$atlasPath
    $bitmap.EndInit()
    $cw = [int][Math]::Floor($bitmap.PixelWidth / 3)
    $ch = [int][Math]::Floor($bitmap.PixelHeight / 2)
    foreach ($pose in @(0, 1, 3, 4)) {
        $crop = New-Object Windows.Int32Rect (($pose % 3)*$cw), ([int][Math]::Floor($pose / 3)*$ch), $cw, $ch
        $frame = New-Object Windows.Media.Imaging.CroppedBitmap $bitmap, $crop
        $frame.Freeze()
        $script:poses += $frame
    }
    $portrait.Source = $script:poses[0]
}

$script:hostStep = 0
$script:hostTicks = 0
function Update-Samurai {
    $script:hostStep++
    $lines = @('使いたい画面を選んでくれ！', '考え中？ ゆっくり選ぼう。', 'ひと言を押すと、僕が応えるぞ。', '今日も、自分のペースでいこう！')
    if ($script:running) {
        $lines = @('ここで待っているぞ。', 'ひと息ついて、肩の力を抜こう。', '操作はアプリの画面で進めよう。', 'あわてず、一歩ずついこう！')
    }
    $talk.Content = $lines[$script:hostStep % $lines.Count]
    if ($script:poses.Count) { $portrait.Source = $script:poses[$script:hostStep % $script:poses.Count] }
}
function Set-SamuraiMotion {
    if ($motion.IsChecked -and [Windows.SystemParameters]::ClientAreaAnimation) {
        $breathe = New-Object Windows.Media.Animation.DoubleAnimation
        $breathe.From = 0
        $breathe.To = -5
        $breathe.Duration = [Windows.Duration]::new([TimeSpan]::FromSeconds(2.4))
        $breathe.AutoReverse = $true
        $breathe.RepeatBehavior = [Windows.Media.Animation.RepeatBehavior]::Forever
        $ease = New-Object Windows.Media.Animation.SineEase
        $ease.EasingMode = [Windows.Media.Animation.EasingMode]::EaseInOut
        $breathe.EasingFunction = $ease
        $float.BeginAnimation([Windows.Media.TranslateTransform]::YProperty, $breathe)
    } else {
        $float.BeginAnimation([Windows.Media.TranslateTransform]::YProperty, $null)
    }
}
$motion.IsChecked = [Windows.SystemParameters]::ClientAreaAnimation
$motion.Add_Checked({ Set-SamuraiMotion })
$motion.Add_Unchecked({ Set-SamuraiMotion })
$talk.Add_Click({ Update-Samurai })
Set-SamuraiMotion

$script:running = $null
$script:launchButton = $null
$script:logPath = $null
function Find-JinPython([string]$directory) {
    $localPython = Join-Path $directory '.venv\Scripts\python.exe'
    if (Test-Path -LiteralPath $localPython) { return $localPython }
    $candidates = @()
    $installedRoot = Join-Path $env:LOCALAPPDATA 'Programs\Python'
    if (Test-Path -LiteralPath $installedRoot) {
        $candidates += Get-ChildItem -LiteralPath $installedRoot -Directory |
            Sort-Object Name -Descending |
            ForEach-Object { Join-Path $_.FullName 'python.exe' }
    }
    $candidates += Get-Command python.exe -All -ErrorAction SilentlyContinue |
        Where-Object { $_.Source -notlike '*\WindowsApps\*' } |
        ForEach-Object { $_.Source }
    foreach ($candidate in ($candidates | Select-Object -Unique)) {
        if (!(Test-Path -LiteralPath $candidate)) { continue }
        try {
            $probe = & $candidate -B -c 'import PySide6, numpy, pyqtgraph, zmq; print(731942)' 2>&1
            if ($LASTEXITCODE -eq 0 -and $probe -contains '731942') { return $candidate }
        } catch { continue }
    }
    return $null
}
function Start-JinApp([string]$folder, [string]$label, $button) {
    $directory = Join-Path $root $folder
    $python = Find-JinPython $directory
    $main = Join-Path $directory 'main.py'
    if (!(Test-Path -LiteralPath $main)) {
        [void][Windows.MessageBox]::Show($window, "起動ファイルが見つかりません。`n$main", '起動できませんでした', 'OK', 'Error')
        return
    }
    if (!$python) {
        $message = "$label の起動環境がまだ準備されていません。`n`n$directory の README.md に従い、以下を実行してください。`n`npy -3.13 -m venv .venv`n.\.venv\Scripts\python.exe -m pip install -r requirements.txt"
        [void][Windows.MessageBox]::Show($window, $message, '初回セットアップのご案内', 'OK', 'Information')
        return
    }
    try {
        $script:logPath = Join-Path ([IO.Path]::GetTempPath()) ("JIN-$folder-" + [Guid]::NewGuid().ToString('N') + '.log')
        # Hidden also hides Qt's first window. Use the GUI interpreter and show the app.
        $guiPython = Join-Path (Split-Path -Parent $python) 'pythonw.exe'
        if (Test-Path -LiteralPath $guiPython) { $python = $guiPython }
        $script:running = Start-Process -FilePath $python -ArgumentList '-B', 'main.py' -WorkingDirectory $directory -WindowStyle Normal -RedirectStandardError $script:logPath -PassThru
        # Retain a process handle before exit; PowerShell 5.1 otherwise loses ExitCode.
        $null = $script:running.Handle
        $script:startedAt = Get-Date
        $script:activeLabel = $label
        $script:launchButton = $button
        $userButton.IsEnabled = $false
        $devButton.IsEnabled = $false
        $status.Text = "$label を起動しています。終了すると、ここで再び選べます。"
        $progress.Visibility = 'Visible'
        $talk.Content = 'アプリを呼び出しているぞ。'
    } catch {
        [void][Windows.MessageBox]::Show($window, $_.Exception.Message, '起動できませんでした', 'OK', 'Error')
    }
}
$userButton.Add_Click({ Start-JinApp 'demo' 'ユーザー版' $userButton })
$devButton.Add_Click({ Start-JinApp 'test2' '開発版' $devButton })
$timer = New-Object Windows.Threading.DispatcherTimer
$timer.Interval = [TimeSpan]::FromMilliseconds(750)
$timer.Add_Tick({
    $script:hostTicks++
    if ($motion.IsChecked -and $script:hostTicks % 8 -eq 0) { Update-Samurai }
    if ($script:running) {
        $script:running.Refresh()
        if (!$script:running.HasExited) {
            if ($script:running.MainWindowHandle -ne 0) {
                $progress.Visibility = 'Collapsed'
                $status.Text = "$script:activeLabel は起動中です。アプリ終了後に再び選べます。"
            } elseif (((Get-Date) - $script:startedAt).TotalSeconds -gt 30) {
                $progress.Visibility = 'Collapsed'
                $status.Text = "画面の表示を確認できません。詳細ログ: $script:logPath"
            }
        }
    }
    if ($script:running -and $script:running.HasExited) {
        $script:running.WaitForExit()
        $exitCode = $script:running.ExitCode
        $script:running.Dispose()
        $script:running = $null
        $progress.Visibility = 'Collapsed'
        $talk.Content = 'おかえり！ おつかれさま。'
        $script:hostTicks = 0
        $userButton.IsEnabled = $true
        $devButton.IsEnabled = $true
        $status.Text = 'おかえりなさい。起動するアプリを選んでください。'
        if ($null -eq $exitCode) {
            $status.Text = 'アプリは終了しました（終了コードを取得できませんでした）。再び選択できます。'
        } elseif ($exitCode -ne 0) {
            $status.Text = 'アプリがエラーで終了しました。起動環境を確認してください。'
            [void][Windows.MessageBox]::Show($window, "アプリがエラーで終了しました（終了コード: $exitCode）。`n`n詳細ログ: $script:logPath", 'アプリの終了', 'OK', 'Error')
        }
    }
})
$window.Add_Closed({
    $timer.Stop()
    $float.BeginAnimation([Windows.Media.TranslateTransform]::YProperty, $null)
})

if ($Preview) {
    # Render the actual panel without starting either application.
    $window.Show()
    $window.UpdateLayout()
    $target = New-Object Windows.Media.Imaging.RenderTargetBitmap ([int]$window.ActualWidth), ([int]$window.ActualHeight), 96, 96, ([Windows.Media.PixelFormats]::Pbgra32)
    $target.Render($window)
    $encoder = New-Object Windows.Media.Imaging.PngBitmapEncoder
    $encoder.Frames.Add([Windows.Media.Imaging.BitmapFrame]::Create($target))
    $stream = [IO.File]::Create((Join-Path $root 'launcher-preview.png'))
    try { $encoder.Save($stream) } finally { $stream.Dispose(); $window.Close() }
} else {
    $timer.Start()
    [void]$window.ShowDialog()
}
